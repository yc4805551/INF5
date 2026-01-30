import requests
import os
import binascii

ANYTHING_API_BASE = "http://localhost:3001/api/v1"
ANYTHING_API_KEY = "XJQMPFD-NRN4WS4-NZBJFJ2-HWQFT7K"
SLUG = "yc" # We know this is 'inf_work'

def hex_dump(data):
    return binascii.hexlify(data).decode('ascii')

def test_prompt(prompt):
    url = f"{ANYTHING_API_BASE}/workspace/{SLUG}/chat"
    headers = {
        "Authorization": f"Bearer {ANYTHING_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = {
        "message": prompt,
        "mode": "chat"
    }
    
    print(f"\n--- Testing Prompt: '{prompt}' ---")
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=300)
        print(f"Status: {response.status_code}")
        
        raw_bytes = response.content
        print(f"Response Bytes Length: {len(raw_bytes)}")
        print(f"Response Hex Head (first 100): {hex_dump(raw_bytes[:100])}")
        
        # Check for Replacement Character (EF BF BD)
        if b'\xef\xbf\xbd' in raw_bytes:
            print("ALERT: Found UTF-8 Replacement Character (EF BF BD) in response!")
            count = raw_bytes.count(b'\xef\xbf\xbd')
            print(f"Count of replacement chars: {count}")
            
        try:
            print(f"Decoded (UTF-8): {raw_bytes.decode('utf-8')[:100]}")
        except:
             print("UTF-8 Decode Failed on full response")

        data = response.json()
        text = data.get('textResponse', '')
        print(f"JSON parsed textResponse: {text}")
        print(f"Text chars: {[c for c in text]}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_prompt("123")
    test_prompt("Hello")
