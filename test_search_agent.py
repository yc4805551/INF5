import sys
import os
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO)

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from dotenv import load_dotenv
load_dotenv('config/.env')
load_dotenv('config/.env.local', override=True)

from features.file_search.search_agent import FileSearchAgent

def test_agent():
    print("Initializing FileSearchAgent...")
    # Use 'gemini' or whatever is configured in .env.local
    # .env.local has VITE_GEMINI_API_KEY, and search_agent uses call_llm which reads env.
    
    agent = FileSearchAgent(model_provider="openai")
    
    queries = [
        "帮我找到碳足迹材料",
        "2024年碳效体系评价指标",
        "帮我找最近关于机器学习的PPT"
    ]
    
    for q in queries:
        print(f"\n--- Testing Query: {q} ---")
        try:
            result = agent.understand_query(q)
            print("Parsed Result:")
            print(result)
        except Exception as e:
            print(f"ERROR: {e}")

if __name__ == "__main__":
    test_agent()
