
import sys
import os
import asyncio
import logging

# 定位到 backend 目录
current_file = os.path.abspath(__file__)
audit_dir = os.path.dirname(current_file) # backend/features/audit
features_dir = os.path.dirname(audit_dir) # backend/features
backend_dir = os.path.dirname(features_dir) # backend

print(f"Adding backend_dir to path: {backend_dir}")
sys.path.insert(0, backend_dir)

# Mock 环境变量
os.environ["OPENAI_API_KEY"] = "sk-mock-key" 
os.environ["OPENAI_BASE_URL"] = "https://api.openai.com/v1"
os.environ["VITE_API_BASE_URL"] = "http://localhost:5000"

logging.basicConfig(level=logging.ERROR)

async def test_realtime():
    print("--- Starting Realtime Check Debug ---")
    try:
        from features.audit.services import perform_realtime_check
        
        # 模拟请求数据
        data = {
            "content": "测试文本，包含提高数量这个搭配不当。",
            "source": "",
            "model_config": {
                "provider": "openai",
                "model": "gpt-3.5-turbo"
            }
        }
        
        print(f"Calling service with: {data}")
        result = await perform_realtime_check(data)
        print("--- Result ---")
        print(result)

    except ImportError as ie:
        print(f"Import Error: {ie}")
        print(f"Sys Path: {sys.path}")
    except Exception as e:
        print(f"Runtime Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_realtime())
