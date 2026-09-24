import os
import time
import httpx
import json
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Security, Depends, Query, BackgroundTasks, status
from fastapi.security import APIKeyHeader
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
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

# Smart auto-detection of Gemini vs OpenAI keys
api_key = os.getenv("OPENAI_API_KEY")
is_gemini = api_key and api_key.startswith("AQ.")
base_url = "https://generativelanguage.googleapis.com/v1beta/openai/" if is_gemini else None
model_name = "models/gemini-3.5-flash-lite" if is_gemini else "gpt-4o-mini"

client = OpenAI(api_key=api_key, base_url=base_url)

TOKEN_STORE = {}
GHL_CLIENT_ID = os.getenv("GHL_CLIENT_ID")
GHL_CLIENT_SECRET = os.getenv("GHL_CLIENT_SECRET")
GHL_REDIRECT_URI = os.getenv("GHL_REDIRECT_URI")
GHL_API_BASE = "https://services.leadconnectorhq.com"

class PropertyEvaluationRequest(BaseModel):
    property_input: str = Field(..., example="Address: 1244 Maplewood Dr, Indianapolis, IN | SqFt: 1850 | Asking: $165,000 | ARV: $260,000 | Condition: Standard rehab needed.")

class GHLWorkflowPayload(BaseModel):
    locationId: str = Field(..., example="loc_xyz123")
    contactId: str = Field(..., example="contact_abc456")
    property_address: Optional[str] = None
    asking_price: Optional[str] = None
    arv: Optional[str] = None
    sqft: Optional[str] = None
    condition: Optional[str] = "Standard rehab needed"

@app.post("/v1/evaluate", response_model=dict, dependencies=[Depends(verify_api_key)], tags=["Core Analysis"])
async def evaluate_property(request: PropertyEvaluationRequest):
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
    scopes = "contacts.readonly contacts.write workflows.readonly"
    auth_url = (
        f"{GHL_API_BASE}/oauth/chooselocation?"
        f"response_type=code&"
        f"client_id={GHL_CLIENT_ID}&"
        f"redirect_uri={GHL_REDIRECT_URI}&"
        f"scope={scopes}"
    )
    return RedirectResponse(auth_url)


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
            "expires_in": token_data.get("expires_in")
        }

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
    location_id = payload.locationId
    token_info = TOKEN_STORE.get(location_id)

    if not token_info:
        print(f"[Error] No active access token found for locationId: {location_id}")
        return

    access_token = token_info["access_token"]

    # Construct deal string for GPT engine
    property_input = (
        f"Address: {payload.property_address or 'N/A'} | "
        f"Asking: {payload.asking_price or 'N/A'} | "
        f"ARV: {payload.arv or 'N/A'} | "
        f"SqFt: {payload.sqft or 'N/A'} | "
        f"Condition: {payload.condition}"
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
    
    mao_val = metrics.get("max_allowable_offer_mao")
    rehab_val = metrics.get("total_estimated_rehab")
    verdict_val = evaluation.get("status")
    
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
            {"key": "mao_price", "field_value": str(mao_val) if mao_val is not None else "N/A"},
            {"key": "rehab_estimate", "field_value": str(rehab_val) if rehab_val is not None else "N/A"},
            {"key": "deal_verdict", "field_value": str(verdict_val) if verdict_val is not None else "N/A"},
            {"key": "underwriting_summary", "field_value": summary_val}
        ]
    }

    async with httpx.AsyncClient() as http_client:
        res = await http_client.put(
            f"{GHL_API_BASE}/contacts/{payload.contactId}",
            json=update_data,
            headers=ghl_headers
        )
        if res.status_code == 200:
            print(f"[Success] Updated GHL Contact {payload.contactId} for location {location_id}")
        else:
            print(f"[Failed] GHL Contact Update Error: {res.text}")


@app.post("/v1/ghl/workflow-action", tags=["GHL Integration"])
async def ghl_workflow_action(payload: GHLWorkflowPayload, background_tasks: BackgroundTasks):
    """
    Endpoint triggered by GoHighLevel Workflows.
    Responds immediately (200 OK) to prevent workflow timeouts and processes analysis in background.
    """
    background_tasks.add_task(process_and_update_ghl_contact, payload)
    return {"status": "queued", "message": "Deal evaluation started for GHL workflow."}


# ==========================================
# 4. HEALTH CHECK DIAGNOSTIC ENDPOINT
# ==========================================

@app.get("/health", tags=["Diagnostics"])
def health_check():
    return {"status": "ok", "service": "DealEngine API"}

