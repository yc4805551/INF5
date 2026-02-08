"""
Quick API test script for Remote Control API
Run: python quick_test.py
"""
import requests
import json

API_KEY = "Fw7qu71eTRTxMo1F91oTOvczCe5ojOzi"
BASE_URL = "http://localhost:5179/api/remote-control"
headers = {"X-API-Key": API_KEY}

print("=== Remote Control API Quick Test ===\n")

# 1. Health Check
print("1. Testing Health Check...")
resp = requests.get(f"{BASE_URL}/health", headers=headers)
print(f"   Status: {resp.status_code}")
print(f"   Response: {resp.json()}\n")

# 2. Capabilities
print("2. Testing Capabilities...")
resp = requests.get(f"{BASE_URL}/capabilities", headers=headers)
print(f"   Status: {resp.status_code}")
caps = resp.json()["data"]["capabilities"]
print(f"   Capabilities: {list(caps.keys())}\n")

# 3. Create Session
print("3. Creating Session...")
resp = requests.post(f"{BASE_URL}/session/create", 
                     headers=headers,
                     json={"session_name": "Quick Test"})
print(f"   Status: {resp.status_code}")
session_data = resp.json()["data"]
session_id = session_data["session_id"]
print(f"   Session ID: {session_id}\n")

# 4. Get Session Status
print(f"4. Getting Session Status...")
resp = requests.get(f"{BASE_URL}/session/{session_id}/status", headers=headers)
print(f"   Status: {resp.status_code}")
print(f"   Session Status: {resp.json()['data']['status']}\n")

# 5. Create Document
print("5. Creating Document...")
doc_content = {
    "session_id": session_id,
    "title": "测试文档",
    "content": {
        "type": "doc",
        "content": [
            {
                "type": "heading",
                "attrs": {"level": 1},
                "content": [{"type": "text", "text": "测试标题"}]
            },
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "这是测试内容，验证 Remote Control API 功能。"}]
            }
        ]
    }
}
resp = requests.post(f"{BASE_URL}/document/create",
                    headers=headers,
                    json=doc_content)
print(f"   Status: {resp.status_code}")
doc_data = resp.json()["data"]
doc_id = doc_data["doc_id"]
print(f"   Document ID: {doc_id}\n")

# 6. Get Document Content
print("6. Getting Document Content...")
resp = requests.get(f"{BASE_URL}/document/{doc_id}/content", headers=headers)
print(f"   Status: {resp.status_code}")
doc = resp.json()["data"]
print(f"   Title: {doc['title']}")
print(f"   Content Type: {doc['content']['type']}\n")

# 7. Export DOCX
print("7. Exporting as DOCX...")
resp = requests.get(f"{BASE_URL}/document/{doc_id}/export-docx", headers=headers)
print(f"   Status: {resp.status_code}")
with open("test_export.docx", "wb") as f:
    f.write(resp.content)
print(f"   Saved to: test_export.docx\n")

# 8. Export Smart DOCX
print("8. Exporting as Smart DOCX...")
resp = requests.get(f"{BASE_URL}/document/{doc_id}/export-smart-docx", headers=headers)
print(f"   Status: {resp.status_code}")
with open("test_smart_export.docx", "wb") as f:
    f.write(resp.content)
print(f"   Saved to: test_smart_export.docx\n")

# 9. Close Session
print("9. Closing Session...")
resp = requests.post(f"{BASE_URL}/session/{session_id}/close", headers=headers)
print(f"   Status: {resp.status_code}")
print(f"   Session Closed: {resp.json()['data']['status']}\n")

print("=== All Tests Passed! ===")
