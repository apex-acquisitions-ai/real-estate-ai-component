import os
import requests
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("INSTANTLY_API_KEY", "MTAzYzg3MjItYTNmYi00ODNhLTk2ZmEtYzg2NDE3ZGMxOWJhOkltc1FiSHp1SVFZSg==")
BASE_URL = "https://api.instantly.ai/api/v2"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# =========================================================================
# Google Workspace Security Configuration Notice:
# =========================================================================
# Since dealenginecore.com, dealenginespecs.com, and rundealengine.com are all
# hosted on Google Workspace, they require Gmail's secure SMTP/IMAP servers.
#
# Crucial Gmail Prerequisites:
# 1. ENABLE IMAP: Log in to Gmail -> Settings -> 'Forwarding and POP/IMAP' 
#    -> select 'Enable IMAP' -> Save Changes.
# 2. GENERATE APP PASSWORD: To connect Google Workspace to Instantly programmatically,
#    you MUST use a Google "App Password" (a 16-character security code).
#    Standard passwords (e.g., 'ozoneOz711$11') are blocked by Google for direct IMAP.
#    How-to: Google Account Settings -> Security -> 2-Step Verification -> App Passwords
#    -> Select App: 'Other', name it 'Instantly', and copy the 16-character code.
# =========================================================================

# List of Google Workspace inboxes and independent seats to provision in Instantly
# Each account runs on its own independent Google Workspace seat with unique passwords.
INBOXES_TO_ADD = [
    # --- Main Domain: dealenginecore.com ---
    {
        "email": "onzieb@dealenginecore.com",
        "first_name": "Onzieb",
        "last_name": "Barnes",
        "smtp_password": os.getenv("DEALENGINECORE_ONZIEB_APP_PWD", "hcrn muhd pabk jrck"),
        "daily_limit": 30
    },
    # --- Secondary Domain 1: dealenginespecs.com ---
    {
        "email": "onzeb@dealenginespecs.com",
        "first_name": "Onzeb",
        "last_name": "Barnes",
        "smtp_password": os.getenv("DEALENGINESPECS_ONZIEB_APP_PWD", "pele fkhd nquc xmba"),
        "daily_limit": 30
    },
    # --- Secondary Domain 2: rundealengine.com ---
    {
        "email": "onzieb@rundealengine.com",
        "first_name": "Onzieb",
        "last_name": "Barnes",
        "smtp_password": os.getenv("RUNDEALENGINE_ONZIEB_APP_PWD", "tkxk jyez vtpv naje"),
        "daily_limit": 30
    }
]

def register_gmail_inbox(account: Dict[str, Any]) -> Dict[str, Any]:
    """Registers a Google Workspace account using secure App Passwords."""
    payload = {
        "email": account["email"],
        "first_name": account["first_name"],
        "last_name": account["last_name"],
        "provider_code": 1,              # 1 = Custom IMAP/SMTP (required for Google App Passwords)
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 465,                # SSL Port
        "smtp_username": account["email"],
        "smtp_password": account["smtp_password"],
        "imap_host": "imap.gmail.com",
        "imap_port": 993,                # SSL Port
        "imap_username": account["email"],
        "imap_password": account["smtp_password"],
        "daily_limit": account["daily_limit"]
    }
    res = requests.post(f"{BASE_URL}/accounts", json=payload, headers=headers)
    return res.json()

def enable_warmup(email: str) -> Dict[str, Any]:
    url = f"{BASE_URL}/accounts/warmup/enable"
    res = requests.post(url, json={"emails": [email]}, headers=headers)
    return res.json()

if __name__ == "__main__":
    print("=== Instantly.ai V2 Google Workspace Provisioner ===")
    print(f"Configured {len(INBOXES_TO_ADD)} email addresses.\n")
    
    for idx, inbox in enumerate(INBOXES_TO_ADD, start=1):
        email = inbox["email"]
        print(f"[{idx}/{len(INBOXES_TO_ADD)}] Connecting {email}...")
        
        reg_res = register_gmail_inbox(inbox)
        
        if "error" in reg_res or reg_res.get("statusCode") == 400:
            print(f"  ❌ Registration Rejected: {reg_res.get('message', reg_res.get('error'))}")
            print("     💡 Tip: Ensure IMAP is enabled in Gmail settings & you are using a 16-character App Password.")
        else:
            print(f"  ✅ Successfully connected to Google Workspace & registered in Instantly.")
            print(f"  -> Launching email warmup sequence...")
            warm_res = enable_warmup(email)
            if "error" in warm_res or warm_res.get("statusCode") == 400:
                print(f"     ⚠️ Warmup activation failed: {warm_res.get('message')}")
            else:
                print(f"     🔥 Warmup Activated!")

