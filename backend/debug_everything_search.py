
import sys
import os
import logging
import json
import requests
from urllib.parse import quote

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from core.everything_client import EverythingClient
from dotenv import load_dotenv

# Load Env (copying logic from app.py)
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', '.env')
load_dotenv(dotenv_path)

# Also load .env.local if it exists
dotenv_local_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', '.env.local')
if os.path.exists(dotenv_local_path):
    load_dotenv(dotenv_local_path, override=True)
    print(f"Loaded config from {dotenv_local_path}")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_everything():
    print("--- Debugging Everything Client ---")
    
    client = EverythingClient()
    query = "5G"
    max_results = 2000
    
    print(f"Base URL: {client.base_url}")
    print(f"Query: {query}")
    print(f"Max Results: {max_results}")
    
    # Manually construct URL to verifying what's being sent
    search_url = f"{client.base_url}/?search={quote(query)}&json=1&count={max_results}&path=1&path_column=1&size=1&size_column=1&dm=1&date_modified_column=1"
    print(f"Request URL: {search_url}")
    
    auth = client._get_auth()
    print(f"Auth: {auth}")

    try:
        response = requests.get(search_url, auth=auth, timeout=5)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            total_available = data.get('totalResults', 'Unknown')
            results = data.get('results', [])
            
            print(f"Total Results Reported by API: {total_available}")
            print(f"Number of Results Returned: {len(results)}")
            
            if len(results) > 0:
                print("\nfirst 3 results:")
                for i, res in enumerate(results[:3]):
                    print(f"  {i+1}. {res.get('name')} | {res.get('path')}")
            else:
                print("No results returned.")
                
            # Check for any implicit filters in the Agent by simulating the agent call
            print("\n--- Checking Agent Logic ---")
            from features.file_search.search_agent import FileSearchAgent
            agent = FileSearchAgent()
            # We want to see what 'understand_query' produces for "5G"
            intent = agent.understand_query("5G")
            print(f"Agent Intent Analysis: {json.dumps(intent, ensure_ascii=False, indent=2)}")
            
        else:
            print("Failed to get valid response.")
            print(response.text)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_everything()
