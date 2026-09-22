# 🏠 Real Estate AI Underwriting & Outreach Component

An instantly deployable, B2B-ready AI engine that evaluates raw property inputs, performs standard wholesale underwriting calculations, detects risk or data gaps, and drafts non-salesy seller outreach scripts (SMS & Email) with **100% mathematical precision**.

---

## 🚀 2-Minute Quickstart (GoHighLevel / Zapier / Make.com)

If you are a GoHighLevel (GHL) builder, Zapier expert, or Make.com creator, you can drop this component into your automation flow in under 2 minutes.

### Step 1: Copy-Paste the System Prompt
In your GHL **"AI Conversational / Prompt Action"** block or Make.com **"OpenAI Create Chat Completion"** module, paste the system prompt below:

> Use the text from [system_prompt.txt](./system_prompt.txt) in this repository.

### Step 2: Enforce the Structured Output JSON Schema
In GHL's **"Response Type: JSON"** or Make.com's **"JSON Schema / Structured Outputs"** settings, copy and paste the raw JSON schema provided below. 
This guarantees that the AI returns *only* structured data without any conversational fluff (no ````json```` wrappers, no introductory words), mapping directly to GHL custom fields or your CRM.

---

## 🛠️ 2-Minute Quickstart for Software Engineers (Python)

If you are integrating this into a backend app, you can use the OpenAI or Gemini SDK directly:

```python
import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from schema import DealEvaluationResponse

load_dotenv()

# Works out-of-the-box with OpenAI or Google Gemini (OpenAI-compatible) keys
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    # Uncomment the line below if you are using a Google Gemini key (starting with AQ.)
    # base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

# 1. Load system prompt instructions
with open("system_prompt.txt", "r") as f:
    system_prompt = f.read()

# 2. Call API with Structured Output Enforcement
response = client.beta.chat.completions.parse(
    model="gpt-4o-mini", # Or "models/gemini-3.5-flash-lite" for Gemini
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Evaluate this property: 1244 Maplewood Dr, Indianapolis, IN. 1850 SqFt. Asking $165k. ARV $260k. Needs new roof, paint, outdated kitchen."}
    ],
    response_format=DealEvaluationResponse,
    temperature=0.1
)

# 3. Print parsed JSON structure
print(json.dumps(response.choices[0].message.parsed.model_dump(), indent=2))
```

---

## 📋 Underwriting Formulas Applied

The AI is constrained to execute these exact calculations:
*   **Estimated Repair Cost** = `SqFt * Rehab Rate + Itemized Additions`
    *   *Cosmetic*: $\$15 - \$25 / \text{SqFt}$
    *   *Standard*: $\$35 - \$50 / \text{SqFt}$
    *   *Full Gut*: $\$60 - \$85+ / \text{SqFt}$
*   **Max Allowable Offer (MAO)** = `(ARV * 0.70) - Estimated Repair Cost - Wholesale Assignment Fee` (Default fee is $\$10,000$ unless specified)
*   **Deal Spread** = `MAO - Asking Price`
*   **Is Viable Deal** = `true` only if `Deal Spread >= 0`

---

## 📦 5-Property Sample Bundle (`/sample_evaluations`)

We have pre-calculated 5 real-world scenarios to prove the component works flawlessly instantly. You can inspect the outputs inside the [sample_evaluations/](./sample_evaluations/) folder:

1.  **`property_1_cosmetic.json`** (Viable Deal) - Cosmetic rehab needed. Standard underwriting formulas evaluate as a viable opportunity.
2.  **`property_2_gut_job.json`** (Viable but High Risk) - Water-damaged property requiring a full gut rehab. Formulates higher rehab rate and shows risk profile.
3.  **`property_3_overpriced.json`** (Non-Viable Deal) - Correctly calculates that the asking price exceeds the Maximum Allowable Offer (MAO), flagging it as non-viable and appending audit warnings.
4.  **`property_4_high_margin.json`** (Highly Viable) - Deeply discounted inherited property demonstrating a high deal spread and immediate marketing outreach assets.
5.  **`property_5_incomplete.json`** (Incomplete Data Fallback) - Tests safety directives. When critical values (like `SqFt` or `ARV`) are missing, the AI sets status to `"INCOMPLETE_DATA"` and populates `audit_flags` instead of hallucinating.

---

## 📐 Structured Output JSON Schema

Copy and paste the schema below directly into your API call configuration or GoHighLevel custom schema block:

```json
{
  "$defs": {
    "OutreachAssets": {
      "properties": {
        "suggested_opening_offer": {
          "title": "Suggested Opening Offer",
          "type": "number"
        },
        "seller_sms_script": {
          "title": "Seller Sms Script",
          "type": "string"
        },
        "seller_email_script": {
          "title": "Seller Email Script",
          "type": "string"
        }
      },
      "required": [
        "suggested_opening_offer",
        "seller_sms_script",
        "seller_email_script"
      ],
      "title": "OutreachAssets",
      "type": "object"
    },
    "PropertySummary": {
      "properties": {
        "address": {
          "title": "Address",
          "type": "string"
        },
        "sqft": {
          "title": "Sqft",
          "type": "integer"
        },
        "asking_price": {
          "title": "Asking Price",
          "type": "number"
        },
        "estimated_arv": {
          "title": "Estimated Arv",
          "type": "number"
        }
      },
      "required": [
        "address",
        "sqft",
        "asking_price",
        "estimated_arv"
      ],
      "title": "PropertySummary",
      "type": "object"
    },
    "UnderwritingMetrics": {
      "properties": {
        "rehab_tier": {
          "description": "Cosmetic, Standard, or Full Gut",
          "title": "Rehab Tier",
          "type": "string"
        },
        "rehab_cost_per_sqft": {
          "title": "Rehab Cost Per Sqft",
          "type": "number"
        },
        "total_estimated_rehab": {
          "title": "Total Estimated Rehab",
          "type": "number"
        },
        "target_wholesale_fee": {
          "title": "Target Wholesale Fee",
          "type": "number"
        },
        "max_allowable_offer_mao": {
          "title": "Max Allowable Offer Mao",
          "type": "number"
        },
        "deal_spread": {
          "title": "Deal Spread",
          "type": "number"
        },
        "is_viable_deal": {
          "title": "Is Viable Deal",
          "type": "boolean"
        }
      },
      "required": [
        "rehab_tier",
        "rehab_cost_per_sqft",
        "total_estimated_rehab",
        "target_wholesale_fee",
        "max_allowable_offer_mao",
        "deal_spread",
        "is_viable_deal"
      ],
      "title": "UnderwritingMetrics",
      "type": "object"
    }
  },
  "properties": {
    "status": {
      "description": "SUCCESS, INCOMPLETE_DATA, or HIGH_RISK_DEAL",
      "title": "Status",
      "type": "string"
    },
    "property_summary": {
      "$ref": "#/$defs/PropertySummary"
    },
    "underwriting_metrics": {
      "$ref": "#/$defs/UnderwritingMetrics"
    },
    "outreach_assets": {
      "$ref": "#/$defs/OutreachAssets"
    },
    "audit_flags": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": [],
      "title": "Audit Flags"
    }
  },
  "required": [
    "status",
    "property_summary",
    "underwriting_metrics",
    "outreach_assets"
  ],
  "title": "DealEvaluationResponse",
  "type": "object"
}
```
