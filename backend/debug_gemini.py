import os
import sys
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Add backend to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(current_dir))

# Load .env from backend root or project root or config dir
load_dotenv(os.path.join(current_dir, ".env")) # backend/.env
load_dotenv(os.path.join(os.path.dirname(current_dir), ".env")) # INFV5/.env
load_dotenv(os.path.join(os.path.dirname(current_dir), "config", ".env")) # INFV5/config/.env

def test_gemini():
    print("--- Gemini API Diagnostic Tool ---")
    
    # Debug paths
    print(f"Current Dir: {current_dir}")
    print(f"Parent Dir: {os.path.dirname(current_dir)}")
    
    # 1. Get API Key
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("[X] Error: GOOGLE_API_KEY environment variable not set.")
        print("Please set it in .env or your environment.")
        return

    print(f"[OK] API Key found: {api_key[:5]}...{api_key[-3:]}")

    client = genai.Client(api_key=api_key)

    # 2. Test Model Listing (if supported by SDK, otherwise skip)
    print("\n--- Testing Model 'gemini-2.5-flash' (User Configured) ---")
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Hello, simply reply 'OK'."
        )
        print(f"[OK] Success! 'gemini-2.5-flash' works. Response: {response.text}")
    except Exception as e:
        print(f"[X] Failed: 'gemini-2.5-flash' does not appear to work.\n   Error: {e}")

    # 3. Test Known Good Models
    known_models = ["gemini-2.0-flash-exp", "gemini-2.5-flash"]
    
    for model_name in known_models:
        print(f"\n--- Testing Model '{model_name}' ---")
        try:
            response = client.models.generate_content(
                model=model_name,
                contents="Hello, simply reply 'OK'."
            )
            print(f"[OK] Success! Response: {response.text}")
        except Exception as e:
            print(f"[X] Failed: {e}")

if __name__ == "__main__":
    test_gemini()
