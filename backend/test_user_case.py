import sys
import os
import asyncio
import logging
import json

# Add backend to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# Mock env
os.environ["DEEPSEEK_API_KEY"] = os.getenv("DEEPSEEK_API_KEY", "")
os.environ["DEEPSEEK_BASE_URL"] = "https://api.deepseek.com/v1"

logging.basicConfig(level=logging.INFO)

async def test_realtime_with_user_text():
    """测试用户提供的文本"""
    print("=== Testing Realtime Check with User Sample ===\n")
    
    try:
        from features.audit.services import perform_realtime_check
        
        # 用户的文本（包含搭配不当错误）
        test_text = "近年来，我国加快了高等教育事业发展的速度和规模，高校进一步扩大了招生范围。"
        
        data = {
            "content": test_text,
            "source": "",
            "model_config": {
                "provider": "deepseek",
                "model": "deepseek-chat"
            }
        }
        
        print(f"Input Text: {test_text}\n")
        print("Calling perform_realtime_check...")
        
        result = await perform_realtime_check(data)
        
        print("\n=== Result ===")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        if result.get("issues"):
            print(f"\n✓ Found {len(result['issues'])} issue(s)")
            for idx, issue in enumerate(result['issues'], 1):
                print(f"\n[Issue {idx}]")
                print(f"  Type: {issue.get('type')}")
                print(f"  Original: {issue.get('original') or issue.get('problematicText')}")
                print(f"  Suggestion: {issue.get('suggestion')}")
                print(f"  Reason: {issue.get('reason')}")
        else:
            print("\n✗ WARNING: No issues detected!")
            print("Expected to find: '加快了...速度和规模' (搭配不当)")

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_realtime_with_user_text())
