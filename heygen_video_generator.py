import os
import sys
import time
import httpx
import argparse

BASE_URL = "https://api.heygen.com/v3"
API_KEY = os.getenv("HEYGEN_API_KEY") or os.getenv("x-api-key")

# Load script from text file if available, otherwise fallback
script_file = "teleprompter_script.txt"
if os.path.exists(script_file):
    with open(script_file, "r", encoding="utf-8") as f:
        DEFAULT_SCRIPT = f.read()
else:
    DEFAULT_SCRIPT = "Hi GHL App Review Team! This is Alex from DealEngine."

def get_headers():
    if not API_KEY or "your_" in API_KEY or API_KEY == "placeholder_key":
        print("❌ Error: HEYGEN_API_KEY environment variable is missing or placeholder.")
        print("Please export HEYGEN_API_KEY in your local shell or .env file.")
        sys.exit(1)
    return {"x-api-key": API_KEY, "Content-Type": "application/json"}

def list_voices(gender=None):
    print("🔍 Fetching English voices from HeyGen...")
    try:
        with httpx.Client() as client:
            res = client.get(f"{BASE_URL}/voices", headers=get_headers(), params={"language": "English", "type": "public"})
            if res.status_code != 200:
                print(f"❌ Error: {res.status_code} - {res.text}")
                return
            voices = res.json().get("data", [])
            print(f"\n✅ Public English Voices (Showing top 20):\n" + "-" * 70)
            count = 0
            for v in voices:
                if count >= 20:
                    break
                if gender and v["gender"].lower() != gender.lower():
                    continue
                print(f"ID: {v['voice_id']} | Name: {v['name']} ({v['gender']})")
                count += 1
    except Exception as e:
        print(f"❌ Connection error: {e}")

def list_avatars():
    print("🔍 Fetching character looks from HeyGen...")
    try:
        with httpx.Client() as client:
            res = client.get(f"{BASE_URL}/avatars/looks", headers=get_headers())
            if res.status_code != 200:
                print(f"❌ Error: {res.status_code} - {res.text}")
                return
            looks = res.json().get("data", [])
            print(f"\n✅ Character Looks (Showing top 15):\n" + "-" * 75)
            for l in looks[:15]:
                print(f"Name: {l.get('name')} ({l.get('gender')}) | Look/Avatar ID: {l.get('id')} | Default Voice ID: {l.get('default_voice_id')}")
    except Exception as e:
        print(f"❌ Connection error: {e}")

def generate_video(avatar_id, voice_id):
    print("🚀 Initiating Video Generation on HeyGen...")
    payload = {
        "type": "avatar",
        "avatar_id": avatar_id,
        "script": DEFAULT_SCRIPT,
        "voice_id": voice_id,
        "aspect_ratio": "16:9",
        "resolution": "1080p",
        "title": "DealEngine GHL Marketplace Demo Video"
    }
    try:
        with httpx.Client() as client:
            res = client.post(f"{BASE_URL}/videos", headers=get_headers(), json=payload)
            if res.status_code not in (200, 201):
                print(f"❌ Rejected: {res.status_code} - {res.text}")
                return
            video_id = res.json().get("data", {}).get("id") or res.json().get("data", {}).get("video_id")
            print(f"🎉 Triggered! Video ID: {video_id}. Rendering on HeyGen servers...")
            
            while True:
                status_res = client.get(f"{BASE_URL}/videos/{video_id}", headers=get_headers())
                if status_res.status_code != 200:
                    time.sleep(10)
                    continue
                data = status_res.json().get("data", {})
                status = data.get("status")
                progress = data.get("progress", 0)
                
                if status == "completed":
                    print(f"\n🔥 RENDERING COMPLETE! 🔥\n📹 Video URL: {data.get('video_url')}")
                    break
                elif status == "failed":
                    print(f"\n❌ Rendering Failed: {data.get('error')}")
                    break
                else:
                    print(f"   [Status]: {status.upper()} | Progress: {progress}%", end="\r")
                    time.sleep(10)
    except Exception as e:
        print(f"❌ Connection error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HeyGen API Video Generator")
    parser.add_argument("--action", choices=["list-voices", "list-avatars", "generate"], required=True)
    parser.add_argument("--avatar_id", default="look_def456")
    parser.add_argument("--voice_id", default="1bd001e7e50f421d891986aad5c8bbd2")
    parser.add_argument("--gender", choices=["male", "female"])
    args = parser.parse_args()

    if not API_KEY:
        from dotenv import load_dotenv
        load_dotenv()
        API_KEY = os.getenv("HEYGEN_API_KEY")

    if args.action == "list-voices":
        list_voices(gender=args.gender)
    elif args.action == "list-avatars":
        list_avatars()
    elif args.action == "generate":
        generate_video(args.avatar_id, args.voice_id)

