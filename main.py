import os
import time
import httpx
import json
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Security, Depends, Query, BackgroundTasks, status
from fastapi.security import APIKeyHeader
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel, Field, AliasChoices
from openai import OpenAI

from schema import DealEvaluationResponse

load_dotenv()

app = FastAPI(
    title="Real Estate Deal Evaluation & GoHighLevel API",
    version="1.0.0",
    description="Deterministic JSON micro-service for ARV, MAO, rehab tiers, outreach scripts, and GHL CRM integration."
)

# API Security Setup
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
VALID_API_KEYS = {os.getenv("TEST_API_KEY", "sk_live_dealengine_12345"): "Internal Sandbox"}

def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key in VALID_API_KEYS:
        return api_key
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API Key")

# Initialize client using your Gemini key and Google's OpenAI-compatible base URL
gemini_key = os.getenv("GEMINI_API_KEY")
openai_key = os.getenv("OPENAI_API_KEY")

# Sanitize inputs (handle empty strings, None, or placeholder strings)
def is_valid_key(key: Optional[str]) -> bool:
    if not key:
        return False
    clean = key.strip()
    return bool(clean and "your_" not in clean and clean != "placeholder_key" and clean != "placeholder_password")

if is_valid_key(gemini_key):
    api_key = gemini_key.strip()
    base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
    model_name = "models/gemini-3.5-flash-lite"
elif is_valid_key(openai_key):
    api_key = openai_key.strip()
    if api_key.startswith("AQ."):
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        model_name = "models/gemini-3.5-flash-lite"
    else:
        base_url = None
        model_name = "gpt-4o-mini"
else:
    # Prevent startup crash on cloud environments (Render/Vercel) when env keys are being loaded
    api_key = "placeholder_key"
    base_url = None
    model_name = "gpt-4o-mini"

client = OpenAI(api_key=api_key, base_url=base_url)

TOKEN_STORE = {}
GHL_CLIENT_ID = os.getenv("GHL_CLIENT_ID")
GHL_CLIENT_SECRET = os.getenv("GHL_CLIENT_SECRET")
GHL_REDIRECT_URI = os.getenv("GHL_REDIRECT_URI")
GHL_API_BASE = "https://services.leadconnectorhq.com"

class PropertyEvaluationRequest(BaseModel):
    property_input: str = Field(..., example="Address: 1244 Maplewood Dr, Indianapolis, IN | SqFt: 1850 | Asking: $165,000 | ARV: $260,000 | Condition: Standard rehab needed.")

class GHLWorkflowPayload(BaseModel):
    location_id: str = Field(..., validation_alias=AliasChoices("location_id", "locationId"), example="loc_xyz123")
    contact_id: str = Field(..., validation_alias=AliasChoices("contact_id", "contactId"), example="contact_abc456")
    address: Optional[str] = Field(None, validation_alias=AliasChoices("address", "property_address"), example="1244 Maplewood Dr")
    city: Optional[str] = Field(None, example="Indianapolis")
    zip_code: Optional[str] = Field(None, example="46201")
    asking_price: Optional[str] = None
    arv: Optional[str] = None
    sqft: Optional[str] = None
    condition: Optional[str] = "Standard rehab needed"

@app.post("/v1/evaluate", response_model=dict, dependencies=[Depends(verify_api_key)], tags=["Core Analysis"])
async def evaluate_property(request: PropertyEvaluationRequest):
    if client.api_key == "placeholder_key":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI Underwriting Engine is missing valid credentials. Please ensure GEMINI_API_KEY or OPENAI_API_KEY is configured in your Render environment variables."
        )
    start_time = time.time()
    try:
        with open("system_prompt.txt", "r", encoding="utf-8") as f:
            system_prompt = f.read()

        response = client.beta.chat.completions.parse(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Evaluate this property:\n{request.property_input}"}
            ],
            response_format=DealEvaluationResponse,
            temperature=0.1
        )

        latency = round(time.time() - start_time, 3)
        output_data = response.choices[0].message.parsed.model_dump()

        telemetry = {
            "status": "success",
            "latency_seconds": latency,
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }

        return {"data": output_data, "telemetry": telemetry}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# ==========================================
# 2. OAUTH 2.0 AUTHORIZATION HANDLERS
# ==========================================

@app.get("/oauth/authorize", tags=["GHL Integration"])
def authorize_ghl():
    """Redirects agency admins to GHL consent page when installing the app."""
    scopes = "contacts.readonly contacts.write locations/customFields.readonly locations/customFields.write workflows.readonly"
    auth_url = (
        f"https://marketplace.gohighlevel.com/oauth/chooselocation?"
        f"response_type=code&"
        f"client_id={GHL_CLIENT_ID}&"
        f"redirect_uri={GHL_REDIRECT_URI}&"
        f"scope={scopes}"
    )
    return RedirectResponse(auth_url)


async def refresh_ghl_token(location_id: str, refresh_token: str) -> Optional[str]:
    """Helper function to exchange a refresh token for a new access token in GHL."""
    payload = {
        "client_id": GHL_CLIENT_ID,
        "client_secret": GHL_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{GHL_API_BASE}/oauth/token",
                data=payload,
                headers=headers
            )
            if res.status_code == 200:
                token_data = res.json()
                TOKEN_STORE[location_id] = {
                    "access_token": token_data.get("access_token"),
                    "refresh_token": token_data.get("refresh_token"),
                    "expires_in": token_data.get("expires_in"),
                    "timestamp_created": time.time()
                }
                print(f"[Success] Automatically refreshed access token for GHL location: {location_id}")
                return token_data.get("access_token")
            else:
                print(f"[Error] Token refresh failed for location {location_id}: {res.text}")
                return None
    except Exception as e:
        print(f"[Error] Connection error during token refresh: {e}")
        return None


async def get_active_access_token(location_id: str) -> Optional[str]:
    """Gets a valid active access token, refreshing it automatically if expired or close to expiration."""
    token_info = TOKEN_STORE.get(location_id)
    if not token_info:
        return None
        
    access_token = token_info.get("access_token")
    refresh_token = token_info.get("refresh_token")
    expires_in = token_info.get("expires_in", 86400)
    timestamp_created = token_info.get("timestamp_created", 0)
    
    # Check if expired or within 5 minutes of expiring
    is_expired = (time.time() - timestamp_created) >= (expires_in - 300)
    
    if is_expired and refresh_token:
        print(f"[Info] Access token for location {location_id} is expired or expiring soon. Initiating refresh...")
        return await refresh_ghl_token(location_id, refresh_token)
        
    return access_token


async def setup_location_custom_fields(location_id: str, access_token: str):
    """
    Executed automatically after token exchange in /oauth/callback.
    Creates DealEngine specific contact custom fields in GHL sub-account.
    """
    fields_to_create = [
        {"name": "DealEngine MAO", "dataType": "MONEY"},
        {"name": "DealEngine Rehab Estimate", "dataType": "MONEY"},
        {"name": "DealEngine Offer Script", "dataType": "LARGE_TEXT"}
    ]
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Version": "2021-07-28",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        # Fetch existing custom fields to avoid duplicate creation errors (400 Bad Request)
        existing_names = set()
        try:
            get_res = await client.get(
                f"{GHL_API_BASE}/locations/{location_id}/customFields",
                headers=headers
            )
            if get_res.status_code == 200:
                data = get_res.json()
                for field in data.get("customFields", []):
                    existing_names.add(field.get("name"))
            else:
                print(f"[Warning] GHL Custom Fields List returned status: {get_res.status_code}, Response: {get_res.text}")
        except Exception as e:
            print(f"[Warning] Failed to fetch existing custom fields: {e}")

        for field in fields_to_create:
            if field["name"] in existing_names:
                print(f"[Info] Custom field '{field['name']}' already exists for location {location_id}. Skipping.")
                continue
                
            res = await client.post(
                f"{GHL_API_BASE}/locations/{location_id}/customFields",
                headers=headers,
                json=field
            )
            if res.status_code in (200, 201):
                print(f"[Success] Created GHL Custom Field '{field['name']}' for location {location_id}")
            else:
                print(f"[Error] Failed to create GHL Custom Field '{field['name']}' for location {location_id}: {res.text}")


@app.get("/oauth/callback", tags=["GHL Integration"])
async def oauth_callback(code: str = Query(...)):
    """Receives auth code from GHL, exchanges it for access/refresh tokens."""
    payload = {
        "client_id": GHL_CLIENT_ID,
        "client_secret": GHL_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": GHL_REDIRECT_URI,
    }
    
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    async with httpx.AsyncClient() as http_client:
        response = await http_client.post(
            f"{GHL_API_BASE}/oauth/token",
            data=payload,
            headers=headers
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail=f"Token exchange failed: {response.text}"
            )

        token_data = response.json()
        location_id = token_data.get("locationId")

        # Save tokens keyed by locationId
        TOKEN_STORE[location_id] = {
            "access_token": token_data.get("access_token"),
            "refresh_token": token_data.get("refresh_token"),
            "expires_in": token_data.get("expires_in"),
            "timestamp_created": time.time()
        }

        # Provision custom fields automatically for this location
        try:
            await setup_location_custom_fields(location_id, token_data.get("access_token"))
        except Exception as e:
            print(f"[Error] Failed to automatically provision custom fields for location {location_id}: {e}")

    return {
        "status": "success",
        "message": "App installed successfully in GoHighLevel!",
        "location_id": location_id
    }


# ==========================================
# 3. GHL WEBHOOK/WORKFLOW ACTION BACKGROUND PROCESSOR
# ==========================================

async def process_and_update_ghl_contact(payload: GHLWorkflowPayload):
    """Background task to run OpenAI/Gemini evaluation and write JSON output back to GHL contact."""
    if client.api_key == "placeholder_key":
        print("[Error] AI Underwriting Engine is missing valid credentials. Background evaluation skipped.")
        return
    location_id = payload.location_id
    access_token = await get_active_access_token(location_id)

    if not access_token:
        print(f"[Error] No active access token (or failed refresh) found for location_id: {location_id}")
        return

    # Construct deal string for GPT engine
    property_input = (
        f"Address: {payload.address or 'N/A'} | "
        f"City: {payload.city or 'N/A'} | "
        f"Zip Code: {payload.zip_code or 'N/A'} | "
        f"Asking: {payload.asking_price or 'N/A'} | "
        f"ARV: {payload.arv or 'N/A'} | "
        f"SqFt: {payload.sqft or 'N/A'} | "
        f"Condition: {payload.condition or 'Standard rehab needed'}"
    )

    # 1. Run deterministic structured evaluation
    with open("system_prompt.txt", "r", encoding="utf-8") as f:
        system_prompt = f.read()

    response = client.beta.chat.completions.parse(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Evaluate this property:\n{property_input}"}
        ],
        response_format=DealEvaluationResponse,
        temperature=0.1
    )

    evaluation = response.choices[0].message.parsed.model_dump()

    # Extract mapped properties from our verified nested DealEvaluationResponse schema
    metrics = evaluation.get("underwriting_metrics", {})
    property_summary = evaluation.get("property_summary", {})
    outreach_assets = evaluation.get("outreach_assets", {})
    
    mao_val = metrics.get("max_allowable_offer_mao")
    rehab_val = metrics.get("total_estimated_rehab")
    verdict_val = evaluation.get("status")
    
    # Extract outreach offer scripts (SMS and Email)
    sms_script = outreach_assets.get("seller_sms_script") or "N/A"
    email_script = outreach_assets.get("seller_email_script") or "N/A"
    combined_offer_script = f"💬 SELLER SMS SCRIPT:\n{sms_script}\n\n✉️ SELLER EMAIL SCRIPT:\n{email_script}"
    
    summary_val = (
        f"Underwritten Address: {property_summary.get('address') or 'N/A'}. "
        f"Rehab Tier: {metrics.get('rehab_tier') or 'N/A'}. "
        f"Deal Spread: ${metrics.get('deal_spread', 0.0):,.2f}. "
        f"Is Viable: {'YES' if metrics.get('is_viable_deal') else 'NO'}."
    )

    # 2. Push evaluation analysis back into GHL Contact Custom Fields
    ghl_headers = {
        "Authorization": f"Bearer {access_token}",
        "Version": "2021-07-28",
        "Content-Type": "application/json"
    }

    # Custom fields mapping (Must match keys configured in your GHL sub-account)
    update_data = {
        "customFields": [
            # Legacy fields for absolute compatibility
            {"key": "mao_price", "field_value": str(mao_val) if mao_val is not None else "N/A"},
            {"key": "rehab_estimate", "field_value": str(rehab_val) if rehab_val is not None else "N/A"},
            {"key": "deal_verdict", "field_value": str(verdict_val) if verdict_val is not None else "N/A"},
            {"key": "underwriting_summary", "field_value": summary_val},
            # Auto-provisioned fields (mapped using official GHL lowercase-snake key conventions)
            {"key": "contact.dealengine_mao", "field_value": str(mao_val) if mao_val is not None else "N/A"},
            {"key": "contact.dealengine_rehab_estimate", "field_value": str(rehab_val) if rehab_val is not None else "N/A"},
            {"key": "contact.dealengine_offer_script", "field_value": combined_offer_script}
        ]
    }

    async with httpx.AsyncClient() as http_client:
        res = await http_client.put(
            f"{GHL_API_BASE}/contacts/{payload.contact_id}",
            json=update_data,
            headers=ghl_headers
        )
        if res.status_code == 200:
            print(f"[Success] Updated GHL Contact {payload.contact_id} for location {location_id}")
        else:
            print(f"[Failed] GHL Contact Update Error: {res.text}")


# FastAPI Non-Blocking Background Task Handler
@app.post("/v1/ghl/workflow-action", tags=["GHL Integration"])
async def ghl_workflow_action(
    payload: GHLWorkflowPayload, 
    background_tasks: BackgroundTasks
):
    """
    Returns HTTP 200 immediately to satisfy GHL's execution window,
    then executes evaluation and contact updates asynchronously.
    """
    background_tasks.add_task(process_and_update_ghl_contact, payload)
    return {"status": "queued", "message": "Deal evaluation executing in background."}


# ==========================================
# 4. HEALTH CHECK DIAGNOSTIC ENDPOINT
# ==========================================

# ==========================================
# 4. HEALTH CHECK & LEGAL ENDPOINTS
# ==========================================

@app.get("/health", tags=["Diagnostics"])
def health_check():
    return {"status": "ok", "service": "DealEngine API"}


@app.get("/privacy", response_class=HTMLResponse, tags=["Legal"])
def privacy_policy():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Privacy Policy - DealEngine</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.6; color: #2d3748; max-width: 800px; margin: 0 auto; padding: 40px 20px; background-color: #f7fafc; }
            .container { background: #ffffff; padding: 40px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            h1 { color: #2b6cb0; border-bottom: 2px solid #e2e8f0; padding-bottom: 12px; }
            h2 { color: #2d3748; margin-top: 30px; border-bottom: 1px solid #edf2f7; padding-bottom: 8px; }
            p, li { color: #4a5568; font-size: 1rem; }
            .highlight { background-color: #ebf8ff; border-left: 4px solid #3182ce; padding: 12px 16px; margin: 20px 0; border-radius: 4px; }
            footer { margin-top: 40px; text-align: center; font-size: 0.9rem; color: #a0aec0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Privacy Policy</h1>
            <p><strong>Last Updated: September 28, 2026</strong></p>
            <p>This Privacy Policy describes how <strong>DealEngine Real Estate Underwriter</strong> ("App") collects, uses, and safeguards data when you install and use our App within your GoHighLevel (GHL) sub-accounts.</p>
            
            <h2>1. Information We Access and Process</h2>
            <p>To provide real estate underwriting automation, the App requests permissions via OAuth 2.0 to access: </p>
            <ul>
                <li><strong>Contact Information:</strong> Street address, city, and zip code to run the AI underwriting.</li>
                <li><strong>Workflows & Location Settings:</strong> Necessary to execute custom workflow actions and auto-provision custom fields.</li>
            </ul>

            <div class="highlight">
                <strong>Zero-Persistence Policy:</strong> The App temporarily processes lead address details to execute AI evaluations, after which the calculated data is written back to your CRM. We do not store or sell your contacts' personal details on our servers.
            </div>

            <h2>2. Data Usage & Third Parties</h2>
            <p>We process accessed data solely to perform calculations and write custom pitch scripts. Property details are securely shared via API with our language model partners (OpenAI / Google Gemini). No personal identifying details of your contacts are sent to these systems.</p>

            <h2>3. Token Storage & Security</h2>
            <p>All GHL API authorization tokens are transmitted via HTTPS and are securely stored. These keys are refreshed automatically before expiring.</p>

            <h2>4. Data Retention</h2>
            <p>We retain your OAuth token details only as long as the App remains installed. If you uninstall the App, all associated access keys are immediately deleted.</p>

            <h2>5. Contact Us</h2>
            <p>✉️ <strong>Support Email:</strong> <a href="mailto:support@rundealengine.com">support@rundealengine.com</a></p>
        </div>
        <footer>&copy; 2026 DealEngine. All rights reserved.</footer>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/terms", response_class=HTMLResponse, tags=["Legal"])
def terms_of_service():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Terms of Service - DealEngine</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.6; color: #2d3748; max-width: 800px; margin: 0 auto; padding: 40px 20px; background-color: #f7fafc; }
            .container { background: #ffffff; padding: 40px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            h1 { color: #2b6cb0; border-bottom: 2px solid #e2e8f0; padding-bottom: 12px; }
            h2 { color: #2d3748; margin-top: 30px; border-bottom: 1px solid #edf2f7; padding-bottom: 8px; }
            p, li { color: #4a5568; font-size: 1rem; }
            .disclaimer { background-color: #fffaf0; border-left: 4px solid #dd6b20; padding: 12px 16px; margin: 20px 0; border-radius: 4px; color: #7b341e; }
            footer { margin-top: 40px; text-align: center; font-size: 0.9rem; color: #a0aec0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Terms of Service</h1>
            <p><strong>Last Updated: September 28, 2026</strong></p>
            <p>By installing or using <strong>DealEngine Real Estate Underwriter</strong> ("App") within your GoHighLevel sub-account, you agree to these Terms of Service.</p>
            
            <h2>1. Description of Service</h2>
            <p>The App provides an automated real estate underwriting micro-service. It reads property address data from your leads, utilizes AI models to estimate property metrics (ARV, Rehab Estimates, MAO), and drafts custom outreach scripts, writing them back to GHL contact custom fields.</p>

            <h2>2. License & Acceptable Use</h2>
            <p>We grant you a limited, non-transferable license to use the App within GHL sub-accounts that you manage. You agree not to use the App to process spam, fraudulent offers, or violate local real estate solicitation rules.</p>

            <div class="disclaimer">
                <strong>⚠️ IMPORTANT AI UNDERWRITING & FINANCIAL DISCLAIMER:</strong><br>
                All calculations, rehab costs, Maximum Allowable Offers (MAO), and outreach scripts generated by the App are automated estimates produced by AI language models. They are for informational and educational purposes only. The App does NOT provide licensed real estate appraisals, structural inspections, or financial advice. Always verify all numbers with a licensed professional before making any financial or investment decisions.
            </div>

            <h2>3. Limitation of Liability</h2>
            <p>To the maximum extent permitted by law, DealEngine and its developers shall not be liable for any direct or indirect financial losses, investment inaccuracies, or damages resulting from your use of the App or its AI-generated estimations.</p>

            <h2>4. Termination</h2>
            <p>We reserve the right to suspend API access for violations of these Terms. You may terminate your use of the service at any time by uninstalling the App from your GHL Integrations settings.</p>

            <h2>5. Contact Information</h2>
            <p>✉️ <strong>Support Email:</strong> <a href="mailto:support@rundealengine.com">support@rundealengine.com</a></p>
        </div>
        <footer>&copy; 2026 DealEngine. All rights reserved.</footer>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

