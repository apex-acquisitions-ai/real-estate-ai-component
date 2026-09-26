import os
import requests
import httpx
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# Instantly API v2 Configuration
# Environment variables are preferred, falling back to the verified test keys
API_KEY = os.getenv("INSTANTLY_API_KEY", "MTAzYzg3MjItYTNmYi00ODNhLTk2ZmEtYzg2NDE3ZGMxOWJhOkltc1FiSHp1SVFZSg==")
CAMPAIGN_ID = os.getenv("INSTANTLY_CAMPAIGN_ID", "bcf7b126-8fa0-4ef8-b693-b7631a779f39")
BASE_URL = "https://api.instantly.ai/api/v2"

_headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# ==========================================
# 1. Synchronous Methods (using requests)
# ==========================================

def get_campaigns() -> Optional[Dict[str, Any]]:
    """
    Fetch all cold email campaigns under the Instantly account.
    """
    url = f"{BASE_URL}/campaigns"
    try:
        response = requests.get(url, headers=_headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"[Sync API Error] Failed to get campaigns. Code: {response.status_code}. Response: {response.text}")
            return None
    except Exception as e:
        print(f"[Sync API Connection Error] {e}")
        return None

def add_lead(campaign_id: str, email: str, first_name: str = "", skip_if_in_workspace: bool = True) -> Optional[Dict[str, Any]]:
    """
    Add a lead to a specific cold email campaign.
    Note: Under Instantly v2, the endpoint to upload campaigns is /leads/add.
    Using /leads directly with a nested payload results in a 400 Bad Request error.
    """
    url = f"{BASE_URL}/leads/add"
    payload = {
        "campaign_id": campaign_id,
        "skip_if_in_workspace": skip_if_in_workspace,
        "leads": [
            {
                "email": email,
                "first_name": first_name
            }
        ]
    }
    try:
        response = requests.post(url, json=payload, headers=_headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"[Sync API Error] Failed to add lead. Code: {response.status_code}. Response: {response.text}")
            return None
    except Exception as e:
        print(f"[Sync API Connection Error] {e}")
        return None

# ==========================================
# 2. Asynchronous Methods (using httpx - perfect for FastAPI integration)
# ==========================================

async def get_campaigns_async() -> Optional[Dict[str, Any]]:
    """
    Asynchronously fetch all cold email campaigns under the Instantly account.
    """
    url = f"{BASE_URL}/campaigns"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=_headers)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"[Async API Error] Failed to get campaigns. Code: {response.status_code}. Response: {response.text}")
                return None
    except Exception as e:
        print(f"[Async API Connection Error] {e}")
        return None

async def add_lead_async(campaign_id: str, email: str, first_name: str = "", skip_if_in_workspace: bool = True) -> Optional[Dict[str, Any]]:
    """
    Asynchronously add a lead to a specific cold email campaign.
    """
    url = f"{BASE_URL}/leads/add"
    payload = {
        "campaign_id": campaign_id,
        "skip_if_in_workspace": skip_if_in_workspace,
        "leads": [
            {
                "email": email,
                "first_name": first_name
            }
        ]
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=_headers)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"[Async API Error] Failed to add lead. Code: {response.status_code}. Response: {response.text}")
                return None
    except Exception as e:
        print(f"[Async API Connection Error] {e}")
        return None

# Verification Execution
if __name__ == "__main__":
    print("=== Testing Sync Instantly.ai V2 Client ===")
    print(f"Using API Key: {API_KEY[:8]}...{API_KEY[-8:]}")
    print(f"Using Campaign ID: {CAMPAIGN_ID}")
    
    # 1. Fetch campaigns
    print("\n[Step 1] Fetching Campaigns...")
    campaigns = get_campaigns()
    if campaigns:
        print("Success! Available campaigns:")
        for camp in campaigns.get("items", []):
            print(f"- Name: '{camp.get('name')}', ID: '{camp.get('id')}'")
    else:
        print("Failed to fetch campaigns.")
        
    # 2. Add lead
    print("\n[Step 2] Adding Test Lead to Campaign...")
    test_email = "outreach_lead_sync@example.com"
    test_name = "AI Lead"
    result = add_lead(campaign_id=CAMPAIGN_ID, email=test_email, first_name=test_name)
    if result and result.get("status") == "success":
        print(f"Success! Lead added.")
        print(f"Response: {result}")
    else:
        print("Failed to add lead.")
