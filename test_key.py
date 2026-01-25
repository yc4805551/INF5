import requests
import json

# 配置
API_KEY = "sk-N9Mk1rosZ6zPE0j7XYSvJXkYdCBiE1wTDwsG93V3cfPkYGuw"
ENDPOINT = "https://www.dmxapi.cn/v1/chat/completions"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

payload = {
    "model": "gpt-4o-mini", # 使用一个通用的模型名尝试
    "messages": [
        {"role": "user", "content": "Hello, verify key."}
    ],
    "max_tokens": 10
}

print(f"Testing API Key: {API_KEY[:5]}...{API_KEY[-4:]}")
print(f"Endpoint: {ENDPOINT}")

try:
    response = requests.post(ENDPOINT, headers=headers, json=payload, timeout=10)
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        print("\n✅ API Key is VALID!")
    elif response.status_code == 401:
        print("\n❌ API Key is INVALID (401 Unauthorized).")
    elif response.status_code == 429:
        print("\n⚠️ API Key is Valid but Quota Exceeded (429).")
    else:
        print(f"\n⚠️ Unexpected status code: {response.status_code}")

except Exception as e:
    print(f"\n❌ Request Failed: {e}")
