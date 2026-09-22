import json
import os
from dotenv import load_dotenv
from openai import OpenAI
from schema import DealEvaluationResponse

# 1. Load Environment Variables
load_dotenv()

# Initialize OpenAI SDK pointing to Gemini's OpenAI-compatible base URL
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

# 2. Read System Prompt File
with open("system_prompt.txt", "r", encoding="utf-8") as f:
    system_prompt = f.read()

# 3. Sample Property Input
sample_property_input = """
Address: 1244 Maplewood Dr, Indianapolis, IN
SqFt: 1850
Beds: 3 | Baths: 2 | Year Built: 1988
Asking Price: $165,000
Target ARV: $260,000
Condition Notes: Needs a new roof, outdated kitchen, and full interior paint. Standard rehab level.
Wholesale Fee Target: $12,000
"""

# 4. Call API with Structured Outputs Enforcement
print("Running Real Estate AI Engine...\n")

response = client.beta.chat.completions.parse(
    model="models/gemini-3.5-flash-lite",  # Low-overhead lite model
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Evaluate this property:\n{sample_property_input}"}
    ],
    response_format=DealEvaluationResponse,
    temperature=0.1
)

# 5. Extract and Format Clean JSON Result
result = response.choices[0].message.parsed.model_dump()

print("--- AI COMPONENT JSON OUTPUT ---")
print(json.dumps(result, indent=2))
