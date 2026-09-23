import os
import threading
import json
from fastapi import FastAPI, Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from typing import List, Optional
from dotenv import load_dotenv

# Import our underwriter engine function
from test_engine import evaluate_deal_api

load_dotenv()

app = FastAPI(
    title="Apex Acquisitions AI & Underwriting Server",
    description="Production-grade API and Webhook endpoint for Real Estate deal evaluation and GHL pipelines.",
    version="1.0.0"
)

# 1. API Key Authentication Setup
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def get_api_key(api_key: str = Security(api_key_header)):
    expected_key = os.getenv("APP_API_KEY", "apex-secret-token-2026")
    if not api_key or api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key authentication header."
        )
    return api_key

# 2. In-Memory Telemetry Stats Storage (Thread-Safe)
telemetry_lock = threading.Lock()
telemetry_stats = {
    "total_deals_processed": 0,
    "successful_deals": 0,
    "incomplete_data_deals": 0,
    "high_risk_deals": 0,
    "total_tokens_consumed": 0,
    "total_latency_seconds": 0.0,
    "average_latency_seconds": 0.0
}

def record_telemetry(deal_status: str, total_tokens: int, latency_seconds: float):
    with telemetry_lock:
        telemetry_stats["total_deals_processed"] += 1
        telemetry_stats["total_tokens_consumed"] += total_tokens
        telemetry_stats["total_latency_seconds"] += latency_seconds
        telemetry_stats["average_latency_seconds"] = round(
            telemetry_stats["total_latency_seconds"] / telemetry_stats["total_deals_processed"], 2
        )
        
        # Categorize deal status based on system prompt statuses
        if deal_status == "SUCCESS":
            telemetry_stats["successful_deals"] += 1
        elif deal_status == "INCOMPLETE_DATA":
            telemetry_stats["incomplete_data_deals"] += 1
        elif deal_status == "HIGH_RISK_DEAL":
            telemetry_stats["high_risk_deals"] += 1

# 3. Pydantic Models for API Requests
class UnderwriteRequest(BaseModel):
    property_input: str = Field(
        ..., 
        description="Raw description or details of the real estate listing to parse and underwrite."
    )

class GHLWebhookRequest(BaseModel):
    address: str = Field(..., description="Street address of the property")
    sqft: int = Field(..., description="Total square footage of the property")
    asking_price: float = Field(..., description="Seller's asking price in USD")
    estimated_arv: float = Field(..., description="Estimated After Repair Value in USD")
    condition: str = Field(..., description="Condition description of the property")
    wholesale_fee_target: Optional[float] = Field(
        10000.0, 
        description="Target wholesale assignment fee (defaults to $10,000)"
    )

# 4. Endpoints Definition
@app.post("/underwrite", tags=["Acquisitions"])
def underwrite_deal(payload: UnderwriteRequest, _=Depends(get_api_key)):
    """
    Accepts raw property listing descriptions, runs acquisitions underwriting math, 
    generates marketing outreach scripts, and tracks token & performance telemetry.
    """
    try:
        result = evaluate_deal_api(payload.property_input)
        
        data = result.get("data", {})
        telemetry = result.get("telemetry", {})
        
        record_telemetry(
            deal_status=data.get("status", "SUCCESS"),
            total_tokens=telemetry.get("total_tokens", 0),
            latency_seconds=telemetry.get("latency_seconds", 0.0)
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Underwriting engine execution failed: {str(e)}"
        )

@app.post("/webhook/ghl", tags=["Webhooks"])
def receive_ghl_webhook(payload: GHLWebhookRequest, _=Depends(get_api_key)):
    """
    Standard webhook endpoint formatted for GoHighLevel pipelines. Parses flat key-value pairs 
    sent by GHL workflow actions, runs underwriting formulas, and returns GHL-mappable metrics.
    """
    formatted_input = f"""
    Address: {payload.address}
    SqFt: {payload.sqft}
    Asking Price: ${payload.asking_price:,.2f}
    Target ARV: ${payload.estimated_arv:,.2f}
    Condition Notes: {payload.condition}
    Wholesale Fee Target: ${payload.wholesale_fee_target:,.2f}
    """
    try:
        result = evaluate_deal_api(formatted_input)
        
        data = result.get("data", {})
        telemetry = result.get("telemetry", {})
        
        record_telemetry(
            deal_status=data.get("status", "SUCCESS"),
            total_tokens=telemetry.get("total_tokens", 0),
            latency_seconds=telemetry.get("latency_seconds", 0.0)
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process GHL webhook: {str(e)}"
        )

@app.get("/telemetry", tags=["Analytics"])
def get_system_telemetry(_=Depends(get_api_key)):
    """
    Securely retrieves current underwriting system metrics, token usage logs, and average latencies.
    """
    with telemetry_lock:
        return telemetry_stats

if __name__ == "__main__":
    import uvicorn
    # Start the local development server on port 8000
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
