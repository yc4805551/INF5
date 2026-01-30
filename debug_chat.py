import requests
import os
import json

ANYTHING_API_BASE = "http://localhost:3001/api/v1"
ANYTHING_API_KEY = "XJQMPFD-NRN4WS4-NZBJFJ2-HWQFT7K"
SLUG = "yc"

def chat(message, mode="chat"):
    url = f"{ANYTHING_API_BASE}/workspace/{SLUG}/chat"
    headers = {
        "Authorization": f"Bearer {ANYTHING_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = {
        "message": message,
        "mode": "query", # Stateless query
        "stream": True
    }
    
    print(f"Sending to {url}, mode=query, stream=True...")
    try:
        response = requests.post(url, headers=headers, json=payload, stream=True, timeout=300)
        print(f"Status: {response.status_code}")
        
        print("--- Stream Output ---")
        for line in response.iter_lines():
            if line:
                print(f"RAW BYTES: {line}")
                try:
                    print(f"Decoded (GB18030): {line.decode('gb18030')}")
                except:
                    pass
                decoded_line = line.decode('utf-8', errors='replace')
                print(f"Chunk: {decoded_line}")
                
    except Exception as e:
        print(f"Error: {e}")
             
    except Exception as e:
        print(f"Error: {e}")

prompt = "Hi"
full_message = "Hi"

print("--- Test 2: Complex Prompt ---")
chat(full_message)
