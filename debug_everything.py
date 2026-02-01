
import sys
import os
# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from backend.core.everything_client import EverythingClient
from dotenv import load_dotenv

# Load env
load_dotenv('config/.env')
load_dotenv('config/.env.local', override=True)


def test_search():
    client = EverythingClient()
    print(f"Connecting to Everything at: {client.base_url}")
    print(f"Auth: {client.username} / {'***' if client.password else 'None'}")
    
    # Test 1: Raw Search
    keyword = "5G"
    print(f"\n--- Test 1: Raw Search '{keyword}' (limit 2000) ---")
    try:
        # We manually construct the URL here just to show the user what's being requested, 
        # or we rely on the client to log it (which goes to backend_debug.log).
        # Let's print the result count directly.
        results = client.search(keyword, max_results=2000)
        print(f"✅ Success!")
        print(f"Total Results Returned: {len(results)}")
        
        if len(results) > 0:
            print("\nSample top 5 results:")
            for i, r in enumerate(results[:5]):
                print(f" [{i+1}] {r['name']} | {r['path']} | {r.get('size', 'N/A')} bytes")
        
        # Analyze extensions
        exts = {}
        for r in results:
            ext = os.path.splitext(r['name'])[1].lower()
            exts[ext] = exts.get(ext, 0) + 1
        
        print("\nFile Extension Distribution:")
        sorted_exts = sorted(exts.items(), key=lambda x: x[1], reverse=True)
        for ext, count in sorted_exts[:10]:
            print(f"  {ext if ext else '(no ext)'}: {count}")

    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 2: Search with Filters (Simulating what SearchAgent DOES)
    print(f"\n--- Test 2: Agent Simulation (search_with_filters) ---")
    print(f"Keyword: '{keyword}'")
    # Note: SearchAgent might be inferring types. Let's try WITHOUT types first, then WITH types.
    print(f"Scenario A: No File Type Filter")
    try:
        results = client.search_with_filters(keywords=keyword, max_results=2000)
        print(f"Count: {len(results)}")
    except Exception as e:
        print(f"Error: {e}")
        
    print(f"\nScenario B: With Common Doc Filters (Simulated)")
    # Simulating what the AI might have inferred
    file_types = ['.docx', '.pdf', '.pptx', '.txt', '.xlsx']
    print(f"Filters: {file_types}")
    try:
        results = client.search_with_filters(keywords=keyword, file_types=file_types, max_results=2000)
        print(f"Count: {len(results)}")
        print(f"Note: If this count is lower (~90), then the AI is likely filtering your 700+ results down to just documents.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_search()
