# -*- coding: utf-8 -*-
import sys
import os
import asyncio
import logging
import json

# 设置控制台编码
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add backend to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

# 【关键修复】加载环境变量
from dotenv import load_dotenv
config_dir = os.path.join(os.path.dirname(backend_dir), 'config')
env_local = os.path.join(config_dir, '.env.local')
env_file = os.path.join(config_dir, '.env')

if os.path.exists(env_local):
    load_dotenv(env_local)
    print(f"已加载环境变量: {env_local}")
elif os.path.exists(env_file):
    load_dotenv(env_file)
    print(f"已加载环境变量: {env_file}")

# 设置详细日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

async def diagnose_realtime():
    """完整诊断实时检查功能"""
    print("=" * 60)
    print("诊断：实时改错功能")
    print("=" * 60)
    
    # 1. 检查环境变量
    print("\n[1] 检查环境变量...")
    providers = ["DEEPSEEK", "OPENAI", "GEMINI", "FREE"]
    found_key = False
    for p in providers:
        api_key = os.getenv(f"{p}_API_KEY") or os.getenv(f"VITE_{p}_API_KEY")
        if api_key:
            print(f"  [OK] {p}_API_KEY: {api_key[:10]}...")
            found_key = True
            break
    
    if not found_key:
        print("  [ERROR] 未找到任何 API Key！")
        return
    
    # 2. 导入模块
    print("\n[2] 导入模块...")
    try:
        from features.audit.services import perform_realtime_check
        from features.audit.agents import get_agent_prompt
        from features.audit.rule_engine import RuleEngine
        print("  [OK] 模块导入成功")
    except Exception as e:
        print(f"  [ERROR] 导入失败: {e}")
        return
    
    # 3. 测试规则引擎
    print("\n[3] 测试规则引擎...")
    test_text = "近年来，我国加快了高等教育事业发展的速度和规模，高校进一步扩大了招生范围。"
    rule_engine = RuleEngine()
    rule_issues = rule_engine.run_checks(test_text)
    print(f"  规则引擎检测到 {len(rule_issues)} 个问题")
    for issue in rule_issues:
        print(f"    - {issue.get('reason')}")
    
    # 4. 测试 Prompt 生成
    print("\n[4] 测试 Prompt 生成...")
    user_typos = rule_engine.get_typos_text()
    prompt = get_agent_prompt("proofread", test_text, "", user_typos=user_typos)
    print(f"  Prompt 长度: {len(prompt)} 字符")
    if "Self-Critique" in prompt:
        print("  [OK] Prompt 包含反思机制")
    else:
        print("  [WARNING] Prompt 未包含反思机制")
    
    # 5. 测试完整流程
    print("\n[5] 测试完整的 perform_realtime_check...")
    data = {
        "content": test_text,
        "source": "",
        "model_config": {
            "provider": "deepseek",
            "model": "deepseek-chat"
        }
    }
    
    try:
        result = await perform_realtime_check(data)
        print(f"\n  返回结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        if result.get("issues"):
            print(f"\n  [SUCCESS] 成功检测到 {len(result['issues'])} 个问题")
            for idx, issue in enumerate(result['issues'], 1):
                print(f"\n  问题 {idx}:")
                print(f"    类型: {issue.get('type')}")
                print(f"    严重性: {issue.get('severity')}")
                print(f"    原文: {issue.get('original') or issue.get('problematicText')}")
                print(f"    建议: {issue.get('suggestion')}")
                print(f"    原因: {issue.get('reason')}")
                if 'confidence' in issue:
                    print(f"    信心: {issue.get('confidence')}")
        else:
            print("\n  [WARNING] 未检测到任何问题")
            print("  可能原因:")
            print("    1. LLM API 调用失败")
            print("    2. LLM 返回格式错误")
            print("    3. Prompt 未生效")
            
    except Exception as e:
        print(f"\n  [ERROR] 执行失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(diagnose_realtime())
