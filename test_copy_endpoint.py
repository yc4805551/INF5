import requests
import sys

def test_copy():
    url = "http://localhost:5179/api/file-search/copy"
    try:
        print(f"Testing {url}...")
        response = requests.post(url, json={"text": "Hello from Debug Script!"})
        
        if response.status_code == 200:
            print("✅ SUCCESS: Backend successfully processed the copy request.")
            print("Check your clipboard inside Windows (Paste into Notepad). It should say 'Hello from Debug Script!'")
        else:
            print(f"❌ FAILED: Backend returned status code {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ FAILED: Could not connect to backend.")
        print("Is the backend server running on port 5179?")
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    test_copy()
