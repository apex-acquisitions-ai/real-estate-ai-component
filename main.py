import os
import time
import json
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Security, Depends, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from openai import OpenAI
from schema import DealEvaluationResponse

load_dotenv()

app = FastAPI(
    title="Real Estate Deal Evaluation Micro-Component API",
    version="1.0.0",
    description="Deterministic JSON micro-service for ARV, MAO, rehab tiers, and outreach scripts."
)

# API Key Security Setup
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Temporary hardcoded key for sandbox testing (Replace with Supabase/Redis lookup in production)
VALID_API_KEYS = {os.getenv("TEST_API_KEY", "sk_live_dealengine_12345"): "Internal Sandbox"}

def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key in VALID_API_KEYS:
        return api_key
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API Key"
    )

# Smart auto-detection of Gemini vs OpenAI keys to ensure zero-config execution
api_key = os.getenv("OPENAI_API_KEY")
is_gemini = api_key and api_key.startswith("AQ.")

base_url = "https://generativelanguage.googleapis.com/v1beta/openai/" if is_gemini else None
model_name = "models/gemini-3.5-flash-lite" if is_gemini else "gpt-4o-mini"

client = OpenAI(api_key=api_key, base_url=base_url)

class PropertyEvaluationRequest(BaseModel):
    property_input: str = Field(
        ..., 
        example="Address: 1244 Maplewood Dr, Indianapolis, IN | SqFt: 1850 | Asking: $165,000 | ARV: $260,000 | Condition: Standard rehab needed."
    )

@app.post("/v1/evaluate", response_model=dict, dependencies=[Depends(verify_api_key)])
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

        # Telemetry Metadata for Investor Dashboards & Metered Billing
        telemetry = {
            "status": "success",
            "latency_seconds": latency,
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }

        return {
            "data": output_data,
            "telemetry": telemetry
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "DealEngine API"}
