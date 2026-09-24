import os, time, httpx
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from openai import OpenAI
from schema import DealEvaluationResponse

load_dotenv()

app = FastAPI(title="Real Estate AI Component - GoHighLevel Integration", version="1.0.0")

# Smart auto-detection of Gemini vs OpenAI keys to ensure zero-config execution
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

# ==========================================
# 1. OAUTH 2.0 AUTHORIZATION HANDLERS
# ==========================================

@app.get("/oauth/authorize")
def authorize_ghl():
    scopes = "contacts.readonly contacts.write workflows.readonly"
    auth_url = f"{GHL_API_BASE}/oauth/chooselocation?response_type=code&client_id={GHL_CLIENT_ID}&redirect_uri={GHL_REDIRECT_URI}&scope={scopes}"
    return RedirectResponse(auth_url)

@app.get("/oauth/callback")
async def oauth_callback(code: str = Query(...)):
    payload = {
        "client_id": GHL_CLIENT_ID, "client_secret": GHL_CLIENT_SECRET,
        "grant_type": "authorization_code", "code": code, "redirect_uri": GHL_REDIRECT_URI,
    }
    async with httpx.AsyncClient() as http_client:
        response = await http_client.post(f"{GHL_API_BASE}/oauth/token", data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Token exchange failed: {response.text}")
        token_data = response.json()
        location_id = token_data.get("locationId")
        TOKEN_STORE[location_id] = {
            "access_token": token_data.get("access_token"), "refresh_token": token_data.get("refresh_token")
        }
    return {"status": "success", "message": "App installed successfully!", "location_id": location_id}

# ==========================================
# 2. GHL WORKFLOW ACTION DATA MODELS
# ==========================================

class GHLWorkflowPayload(BaseModel):
    locationId: str
    contactId: str
    property_address: Optional[str] = None
    asking_price: Optional[str] = None
    arv: Optional[str] = None
    sqft: Optional[str] = None
    condition: Optional[str] = "Standard rehab needed"

# ==========================================
# 3. CUSTOM WORKFLOW ACTION ENDPOINT
# ==========================================

async def process_and_update_ghl_contact(payload: GHLWorkflowPayload):
    location_id = payload.locationId
    token_info = TOKEN_STORE.get(location_id)
    if not token_info:
        print(f"[Error] No active access token found for locationId: {location_id}")
        return

    access_token = token_info["access_token"]
    property_input = f"Address: {payload.property_address or 'N/A'} | Asking: {payload.asking_price or 'N/A'} | ARV: {payload.arv or 'N/A'} | SqFt: {payload.sqft or 'N/A'} | Condition: {payload.condition}"

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

    metrics = evaluation.get("underwriting_metrics", {})
    prop_summary = evaluation.get("property_summary", {})
    mao_val = metrics.get("max_allowable_offer_mao")
    rehab_val = metrics.get("total_estimated_rehab")
    verdict_val = evaluation.get("status")
    
    summary_val = f"Underwritten: {prop_summary.get('address') or 'N/A'}. Rehab Tier: {metrics.get('rehab_tier') or 'N/A'}. Spread: ${metrics.get('deal_spread', 0.0):,.2f}. Viable: {'YES' if metrics.get('is_viable_deal') else 'NO'}."

    ghl_headers = {"Authorization": f"Bearer {access_token}", "Version": "2021-07-28", "Content-Type": "application/json"}
    update_data = {
        "customFields": [
            {"key": "mao_price", "field_value": str(mao_val) if mao_val is not None else "N/A"},
            {"key": "rehab_estimate", "field_value": str(rehab_val) if rehab_val is not None else "N/A"},
            {"key": "deal_verdict", "field_value": str(verdict_val) if verdict_val is not None else "N/A"},
            {"key": "underwriting_summary", "field_value": summary_val}
        ]
    }

    async with httpx.AsyncClient() as http_client:
        res = await http_client.put(f"{GHL_API_BASE}/contacts/{payload.contactId}", json=update_data, headers=ghl_headers)
        if res.status_code == 200:
            print(f"[Success] Updated GHL Contact {payload.contactId} for location {location_id}")
        else:
            print(f"[Failed] GHL Contact Update Error: {res.text}")

@app.post("/v1/ghl/workflow-action")
async def ghl_workflow_action(payload: GHLWorkflowPayload, background_tasks: BackgroundTasks):
    background_tasks.add_task(process_and_update_ghl_contact, payload)
    return {"status": "queued", "message": "Deal evaluation started for GHL workflow."}
