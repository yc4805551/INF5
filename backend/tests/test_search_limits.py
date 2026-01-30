
import sys
import os
import logging
from unittest.mock import MagicMock, patch

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from features.file_search.search_agent import FileSearchAgent
from features.file_search.tool import execute

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_search_limits():
    """
    Test that the file search agent and tool respect the increased limits.
    """
    print("Testing File Search Limits...")
    
    # Mock EverythingClient search_with_filters to return many results
    mock_results = []
    # Test with 1600 results to exceed previous 1000 limit but stay within new 2000 limit
    for i in range(1600):
        mock_results.append({
            'name': f'file_{i}.txt',
            'path': f'C:\\files\\file_{i}.txt',
            'size': 1024,
            'date_modified': '2023-01-01'
        })
        
    # Patch the EverythingClient used inside services.py
    with patch('features.file_search.services.EverythingClient') as MockClient:
        # Configure the mock instance
        mock_instance = MockClient.return_value
        mock_instance.search_with_filters.return_value = mock_results
        
        # Test 1: Direct Agent Call with high limit
        print("\n[Test 1] Testing FileSearchAgent.smart_search with max_candidates=2000...")
        agent = FileSearchAgent()
        
        # Mock understand_query to return a simple strategy to avoid LLM call
        agent.understand_query = MagicMock(return_value={
            'strategies': [{'keywords': ['test'], 'desc': 'test strategy'}],
            'intent': 'test',
            'file_types': [],
            'time_range': ''
        })
        
        # Mock intelligent_filter to return all candidates (bypass LLM filtering for test)
        agent.intelligent_filter = MagicMock(side_effect=lambda query, candidates, top_k: candidates[:top_k])
        
        # Call with limits high enough to get > 50 results
        result = agent.smart_search(
            natural_language_query="test query",
            everything_search_func=mock_instance.search_with_filters,
            max_candidates=2000,
            top_k=200
        )
        
        num_results = len(result['results'])
        print(f"Results returned: {num_results}")
        
        if num_results >= 200:
            print("PASS: Agent returned >= 200 results")
        else:
            print(f"FAIL: Agent returned {num_results} results, expected >= 200")
            
        # Test 2: Tool Execution
        print("\n[Test 2] Testing tool.execute with max_results=50...")
        
        # Patch the class where it is defined, so the local import in tool.py picks up the mock
        with patch('features.file_search.search_agent.FileSearchAgent', return_value=agent):
            with patch('features.file_search.services.FileSearchService') as MockService:
                MockService.return_value.everything_client = mock_instance
                
                # Execute tool
                tool_output = execute(query="test query", max_results=50)
                
                # Parse output to count items (looking for markdown list items)
                lines = tool_output.split('\n')
                item_count = sum(1 for line in lines if line.strip().startswith('**') and '. ' in line)
                
                print(f"Tool output item count: {item_count}")
                
                if item_count >= 50:
                    print("PASS: Tool returned >= 50 items")
                else:
                    print(f"FAIL: Tool output contained {item_count} items")

if __name__ == "__main__":
    test_search_limits()
