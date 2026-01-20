import requests
import json
import os

def test_everything_raw():
    url = "http://localhost:292"
    auth = ("yc", "abcd1234") # Found in .env.local
    query = "2024-35"
    
    params = {
        "search": query,
        "json": 1,
        "count": 1,
        "path": 1,
        "path_column": 1, # Try this for Everything 1.5?
        "size": 1,
        "size_column": 1,
        "dm": 1,
        "date_modified_column": 1
    }
    
    print(f"Querying Everything at {url} with extended params...")
    try:
        response = requests.get(url, params=params, auth=auth, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("--- Raw JSON Response ---")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            results = data.get("results", [])
            if results:
                print("\n--- First Result Keys ---")
                print(results[0].keys())
            else:
                print("\nNo results found.")
        else:
            print(f"Error: {response.status_code}")
            
    except Exception as e:
        print(f"Failed on port 292: {e}")
        # Try finding the port from likely running processes or config
        # But wait, app.py defaults to 292. Let's assume that for now.

if __name__ == "__main__":
    test_everything_raw()
