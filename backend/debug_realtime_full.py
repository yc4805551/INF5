import os
import sys
import logging
from dotenv import load_dotenv

# Setup Paths
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))) # Project Root
sys.path.append(os.path.dirname(current_dir)) # Backend

# Load Env
load_dotenv(os.path.join(current_dir, ".env")) # backend/.env
load_dotenv(os.path.join(os.path.dirname(current_dir), ".env")) # INFV5/.env
load_dotenv(os.path.join(os.path.dirname(current_dir), "config", ".env")) # INFV5/config/.env

# Setup Logging
logging.basicConfig(level=logging.INFO)

from backend.features.advisor.services import AdvisorService

def test_advisor():
    print("--- Testing Advisor Service (End-to-End) ---")
    
    service = AdvisorService()
    
    # Test Data: A sentence with typos
    text = "这个产品的性价比如此之高，真的是太牛逼了，但是有时候会出现卡顿的情况。"
    context = "用户正在撰写一篇产品评测。"
    
    # Config: passing a dummy key or relying on Env
    # Note: If env key is missing, this relies on what we just fixed (auto-fetch)
    # But usually frontend passes key. Let's try WITHOUT explicit key first (Env test)
    config = {
        "provider": "gemini",
        "model": "gemini-2.5-flash"
        # "apiKey": "..." # Let it use Env
    }
    
    print(f"\n[1] Testing with Env Key (Config has no Key)...")
    try:
        suggestions = service.generate_suggestions(text, context, config)
        print(f"Result count: {len(suggestions)}")
        for i, s in enumerate(suggestions):
            print(f"  [{i}] {s.get('type')}: {s.get('original')} -> {s.get('suggestion')} ({s.get('reason')})")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_advisor()
