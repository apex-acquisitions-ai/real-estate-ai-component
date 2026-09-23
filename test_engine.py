import json
import os
import time
from dotenv import load_dotenv
from openai import OpenAI
from schema import DealEvaluationResponse

load_dotenv()

# Smart auto-detection of Gemini vs OpenAI keys to ensure zero-config execution
api_key = os.getenv("OPENAI_API_KEY")
is_gemini = api_key and api_key.startswith("AQ.")

base_url = "https://generativelanguage.googleapis.com/v1beta/openai/" if is_gemini else None
model_name = "models/gemini-3.5-flash-lite" if is_gemini else "gpt-4o-mini"

client = OpenAI(api_key=api_key, base_url=base_url)

def evaluate_deal_api(property_input: str):
    start_time = time.time()
    
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
    
    latency = round(time.time() - start_time, 2)
    output_data = response.choices[0].message.parsed.model_dump()
    
    # Telemetry metadata for investor tracking
    telemetry = {
        "latency_seconds": latency,
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "total_tokens": response.usage.total_tokens
    }
    
    return {"data": output_data, "telemetry": telemetry}

if __name__ == "__main__":
    sample_input = "Address: 1244 Maplewood Dr, Indianapolis, IN | SqFt: 1850 | Asking: $165,000 | ARV: $260,000 | Condition: Standard rehab needed."
    res = evaluate_deal_api(sample_input)
    print(json.dumps(res, indent=2))
