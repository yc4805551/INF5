import requests

ANYTHING_API_BASE = "http://localhost:3001/api/v1"
ANYTHING_API_KEY = "XJQMPFD-NRN4WS4-NZBJFJ2-HWQFT7K"

def list_workspaces():
    url = f"{ANYTHING_API_BASE}/workspaces"
    headers = {
        "Authorization": f"Bearer {ANYTHING_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    print(f"Fetching workspaces from {url}...")
    try:
        response = requests.get(url, headers=headers)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            workspaces = response.json().get('workspaces', [])
            print(f"Found {len(workspaces)} workspaces:")
            for ws in workspaces:
                print(f"- Name: {ws.get('name')}, Slug: {ws.get('slug')}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    list_workspaces()
