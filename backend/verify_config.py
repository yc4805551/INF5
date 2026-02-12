
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), 'backend')))

from core.llm_config import LLMConfigManager
from features.smart_file_agent import config as sfa_config

def test_config_resolution():
    print("--- Testing LLMConfigManager Defaults ---")
    cm = LLMConfigManager()
    
    ali_config = cm.get_provider_config("aliyun")
    print(f"Aliyun Config: {ali_config}")
    
    print("\n--- Testing SmartFileAgent Config Logic ---")
    ocr_provider = sfa_config.OCR_MODEL_PROVIDER
    print(f"Default OCR Provider: {ocr_provider}")
    
    # Simulate logic from SmartFileAgent.__init__
    if ocr_provider == "aliyun":
        provider_config = cm.get_provider_config(ocr_provider)
        api_key = provider_config.get("apiKey")
        endpoint = provider_config.get("endpoint")
        print(f"Resolved API Key for Aliyun: {api_key}")
        print(f"Resolved Endpoint for Aliyun: {endpoint}")
    else:
        print(f"OCR Provider {ocr_provider} is not aliyun, skipping simulation.")

if __name__ == "__main__":
    test_config_resolution()
