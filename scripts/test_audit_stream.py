import requests
import json
import time

URL = "http://localhost:5179/api/audit/analyze"

def test_stream():
    payload = {
        "content": "Tests content for streaming.",
        "source": "Source reference.",
        "stream": True,
        "model_config": {} # No API Key => Mock
    }
    
    print(f"Connecting to {URL} with stream=True...")
    try:
        with requests.post(URL, json=payload, stream=True) as r:
            if r.status_code != 200:
                print(f"Error: {r.status_code} - {r.text}")
                return

            print("--- Stream Start ---")
            for chunk in r.iter_content(chunk_size=None):
                if chunk:
                    print(f"[Chunk]: {chunk.decode('utf-8')}")
            print("\n--- Stream End ---")
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_stream()
