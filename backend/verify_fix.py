
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), 'backend')))

# Mock Environment Variable BEFORE importing config manager
os.environ["DASHSCOPE_API_KEY"] = "sk-mock-dashscope-key"
os.environ["ALI_API_KEY"] = "" # Ensure ALI key is empty to test fallback

from core.llm_config import LLMConfigManager

def test_config_resolution():
    print("--- Testing LLMConfigManager w/ DashScope Key ---")
    cm = LLMConfigManager()
    
    ali_config = cm.get_provider_config("aliyun")
    print(f"Aliyun Config: {ali_config}")
    
    if ali_config['apiKey'] == "sk-mock-dashscope-key":
        print("SUCCESS: Resolved API Key from DASHSCOPE_API_KEY")
    else:
        print(f"FAILURE: Expected 'sk-mock-dashscope-key', got '{ali_config['apiKey']}'")

    if ali_config['endpoint'] == "https://dashscope.aliyuncs.com/compatible-mode/v1":
        print("SUCCESS: Resolved Default Endpoint")
    else:
        print(f"FAILURE: Expected 'https://dashscope.aliyuncs.com/compatible-mode/v1', got '{ali_config['endpoint']}'")

if __name__ == "__main__":
    test_config_resolution()
