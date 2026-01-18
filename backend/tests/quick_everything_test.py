"""
简单的 Everything 连接测试
用于快速验证 Everything HTTP 服务是否可用
"""
import requests

# 配置
URL = "http://localhost:292"
USERNAME = "yc"
PASSWORD = "abcd1234"

print("Testing Everything HTTP Service...")
print(f"URL: {URL}")
print(f"Username: {USERNAME}")

try:
    # 测试基本连接
    response = requests.get(
        f"{URL}/?search=*.txt&json=1&count=1",
        auth=(USERNAME, PASSWORD) if USERNAME else None,
        timeout=5
    )
    
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("[OK] Everything service is running!")
        print(f"Total results: {data.get('totalResults', 0)}")
        if data.get('results'):
            print(f"First result: {data['results'][0].get('name')}")
    elif response.status_code == 401:
        print("[FAIL] Authentication failed! Check username/password")
    else:
        print(f"[WARN] Unexpected status code: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        
except requests.exceptions.ConnectionError:
    print("\n[FAIL] Cannot connect to Everything HTTP server!")
    print("Please check:")
    print("  1. Is Everything running?")
    print("  2. Is HTTP server enabled? (Tools -> Options -> HTTP Server)")
    print(f"  3. Is port 292 correct?")
    
except Exception as e:
    print(f"\n[ERROR] {type(e).__name__}: {e}")
