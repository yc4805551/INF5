import requests
import json

url = "http://localhost:5179/api/agent-anything/smart-write"
payload = {"prompt": "Test prompt"}

try:
    print(f"POST {url} ...")
    response = requests.post(url, json=payload, timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
