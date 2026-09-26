import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("INSTANTLY_API_KEY", "MTAzYzg3MjItYTNmYi00ODNhLTk2ZmEtYzg2NDE3ZGMxOWJhOkltc1FiSHp1SVFZSg==")
CAMPAIGN_ID = os.getenv("INSTANTLY_CAMPAIGN_ID", "bcf7b126-8fa0-4ef8-b693-b7631a779f39")
SUBSEQUENCE_ID = "41d1da6f-f5ea-4dee-b6ab-5425e529a163"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# 1. Update Campaign Level Settings
# - Daily Sending Limit: Cap at 30
# - Deliverability Protection: Disable open tracking to maximize deliverability
print("=== Step 1: Configuring Campaign settings ===")
campaign_payload = {
    "daily_limit": 30,
    "open_tracking": False
}
campaign_res = requests.patch(
    f"https://api.instantly.ai/api/v2/campaigns/{CAMPAIGN_ID}",
    json=campaign_payload,
    headers=headers
)
print(f"Campaign Settings Status: {campaign_res.status_code}")
if campaign_res.status_code == 200:
    print("✅ Campaign settings updated successfully.")
else:
    print(f"❌ Failed to update campaign settings: {campaign_res.text}")


# 2. Update Sequence Email Steps (Subsequence)
# Email 1: Day 0 (A/B Test Variants)
# Email 2: Day 3 (Follow-up)
# Email 3: Day 7 (Breakup - 4 days relative delay from Step 2)
print("\n=== Step 2: Configuring Sequence Steps ===")

email_1_body = (
    "Hey {{firstName}},\n\n"
    "Quick question—are your real estate clients manually calculating MAO and rehab estimates, "
    "or do you have that automated inside their GoHighLevel workflows yet?\n\n"
    "We built a micro-component API that connects natively to GHL. When a property lead enters "
    "a pipeline, it instantly calculates MAO, rehab tiers, and optimal offer scripts, pushing "
    "the structured JSON right back into the contact custom fields.\n\n"
    "Even better: you can rebill this to your client sub-accounts using the GHL Agency Wallet "
    "with a 2x-4x markup (turning underwriting into a passive profit center for {{companyName}}).\n\n"
    "Open to taking a look at a 60-second video demo showing how it works inside GHL?\n\n"
    "Best,\n\n"
    "Onzie\n"
    "Founder, DealEngine"
)

email_2_body = (
    "Hey {{firstName}},\n\n"
    "Following up on this. \n\n"
    "Most GHL agencies handling real estate accounts spend hours setting up complex, fragile "
    "Make or Zapier webhooks to handle deal evaluation—or they rely on acquisitions reps "
    "to enter numbers manually.\n\n"
    "We created a pre-built GHL Snapshot that plugs straight into our API. It maps all "
    "custom fields, pipelines, and automated SMS triggers out of the box so you don't "
    "have to build anything from scratch.\n\n"
    "Would you be against me sending over a quick sandbox link where you can test an "
    "address and see the JSON output in real-time?\n\n"
    "Best,\n\n"
    "Onzie"
)

email_3_body = (
    "Hey {{firstName}},\n\n"
    "I know you're busy running {{companyName}}, so I'll keep this brief.\n\n"
    "If automated real estate underwriting and adding a secondary SaaS revenue stream "
    "aren't priorities for your agency right now, no worries at all.\n\n"
    "If you ever want to see how other GHL agencies are white-labeling our deal evaluation "
    "API for their clients, you can check out the developer specs anytime at dealenginespecs.com.\n\n"
    "Should I close the loop on this for now?\n\n"
    "Best,\n\n"
    "Onzie"
)

subsequence_payload = {
    "sequences": [
        {
            "steps": [
                {
                    "type": "email",
                    "delay": 0,
                    "variants": [
                        {
                            "subject": "quick question re {{companyName}} + GHL",
                            "body": email_1_body
                        },
                        {
                            "subject": "automated deal underwriting for {{companyName}}",
                            "body": email_1_body
                        }
                    ]
                },
                {
                    "type": "email",
                    "delay": 3,
                    "variants": [
                        {
                            "subject": "Re: quick question re {{companyName}} + GHL",
                            "body": email_2_body
                        }
                    ]
                },
                {
                    "type": "email",
                    "delay": 4, # 4 days after Day 3 step = Day 7
                    "variants": [
                        {
                            "subject": "Re: quick question re {{companyName}} + GHL",
                            "body": email_3_body
                        }
                    ]
                }
            ]
        }
    ]
}

subsequence_res = requests.patch(
    f"https://api.instantly.ai/api/v2/subsequences/{SUBSEQUENCE_ID}",
    json=subsequence_payload,
    headers=headers
)
print(f"Subsequence Update Status: {subsequence_res.status_code}")
if subsequence_res.status_code == 200:
    print("✅ Campaign sequence steps updated successfully.")
else:
    print(f"❌ Failed to update sequence steps: {subsequence_res.text}")
