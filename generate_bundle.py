import os
import json
import time
from dotenv import load_dotenv
from openai import OpenAI
from schema import DealEvaluationResponse

# Load environment variables
load_dotenv()

# Initialize client using your Gemini key and Google's OpenAI-compatible base URL
gemini_key = os.getenv("GEMINI_API_KEY")
openai_key = os.getenv("OPENAI_API_KEY")
api_key = gemini_key if gemini_key else openai_key
base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"

client = OpenAI(api_key=api_key, base_url=base_url)

# Read System Prompt File
with open("system_prompt.txt", "r", encoding="utf-8") as f:
    system_prompt = f.read()

# Define the 5 properties
properties = [
    {
        "filename": "property_1_cosmetic.json",
        "description": "Property 1: Cosmetic Rehab (Viable Deal)",
        "input": """
        Address: 4321 Oak Ave, Orlando, FL 32801
        SqFt: 1400
        Beds: 3 | Baths: 2 | Year Built: 1995
        Asking Price: $180,000
        Target ARV: $310,000
        Condition Notes: Property is in decent shape, but outdated. Needs cosmetic rehab: new carpet, fresh interior paint, and modern light fixtures. Overall solid structure.
        Wholesale Fee Target: $10,000
        """
    },
    {
        "filename": "property_2_gut_job.json",
        "description": "Property 2: Major Gut Job (Viable but High Risk/Capital Intensive)",
        "input": """
        Address: 789 Pine Rd, Detroit, MI 48201
        SqFt: 2200
        Beds: 4 | Baths: 2.5 | Year Built: 1940
        Asking Price: $45,000
        Target ARV: $240,000
        Condition Notes: Property has been vacant for 5 years. Severe water damage, completely stripped plumbing, holes in roof, and structural sagging. Requires a Full Gut rehab.
        Wholesale Fee Target: $15,000
        """
    },
    {
        "filename": "property_3_overpriced.json",
        "description": "Property 3: Over-priced Asking (Non-Viable)",
        "input": """
        Address: 555 Sunshine Blvd, Tampa, FL 33606
        SqFt: 1600
        Beds: 3 | Baths: 2 | Year Built: 2002
        Asking Price: $320,000
        Target ARV: $380,000
        Condition Notes: Outdated kitchen and bathrooms, peeling exterior wood paint, minor drywall patching needed. Standard cosmetic/standard rehab tier.
        Wholesale Fee Target: $10,000
        """
    },
    {
        "filename": "property_4_high_margin.json",
        "description": "Property 4: High-Margin Wholesale Deal (Highly Viable)",
        "input": """
        Address: 101 Peachtree St, Atlanta, GA 30303
        SqFt: 1200
        Beds: 2 | Baths: 1 | Year Built: 1965
        Asking Price: $90,000
        Target ARV: $210,000
        Condition Notes: Inherited property from distressed out-of-state heir who wants an immediate cash sale. Needs standard updates (kitchen, bath, HVAC outdated but working). No structural issues.
        Wholesale Fee Target: $10,000
        """
    },
    {
        "filename": "property_5_incomplete.json",
        "description": "Property 5: Incomplete Data / Missing Fields (Fails verification)",
        "input": """
        Address: 999 Unknown Way, Houston, TX 77001
        SqFt: [Unknown / Missing]
        Beds: 3 | Baths: 2 | Year Built: 1980
        Asking Price: $150,000
        Target ARV: [Unknown / Missing]
        Condition Notes: Distressed estate sale. We don't have the square footage or the After Repair Value. Need to inspect.
        Wholesale Fee Target: $10,000
        """
    }
]

# Ensure output directory exists
output_dir = "sample_evaluations"
os.makedirs(output_dir, exist_ok=True)

print("Starting 5-Property Sample Bundle Generation...")

for p in properties:
    print(f"\nEvaluating: {p['description']}")
    
    try:
        response = client.beta.chat.completions.parse(
            model="models/gemini-3.5-flash-lite",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Evaluate this property:\n{p['input']}"}
            ],
            response_format=DealEvaluationResponse,
            temperature=0.1
        )
        
        # Format and dump JSON
        result = response.choices[0].message.parsed.model_dump()
        file_path = os.path.join(output_dir, p["filename"])
        
        with open(file_path, "w", encoding="utf-8") as out_f:
            json.dump(result, out_f, indent=2)
            
        print(f"-> Saved: {file_path}")
        
    except Exception as e:
        print(f"Error evaluating {p['description']}: {e}")
    
    # Sleep to avoid any rate limit spikes
    time.sleep(2.0)

print("\nAll 5 property evaluations completed.")
