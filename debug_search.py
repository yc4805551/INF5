import requests
import json
import sys

def debug_search():
    url = "http://localhost:5179/api/file-search/smart"
    query = "2024-35" # Using the query from the screenshot
    
    payload = {
        "query": query,
        "maxResults": 5,
        "modelProvider": "gemini"
    }
    
    try:
        print(f"Searching for '{query}'...")
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            print(f"Found {len(results)} results.\n")
            
            for i, res in enumerate(results):
                print(f"--- Result {i+1} ---")
                print(f"Name: {res.get('name')}")
                print(f"Path: '{res.get('path')}' (Type: {type(res.get('path'))})")
                print(f"Full Entry: {json.dumps(res, ensure_ascii=False)}")
                
                if not res.get('path'):
                    print("⚠️ WARNING: Path is empty or None!")
        else:
            print(f"Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    debug_search()
