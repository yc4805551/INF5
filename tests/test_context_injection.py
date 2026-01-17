"""
测试：验证AgentEngine动态注入画布和参考文档信息
"""
import sys
import os

# 添加backend到path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from core.docx_engine import DocxEngine
from core.services import current_engine
from features.smart_filler.agent_engine import AgentEngine
from features.smart_filler.services import SmartFillerService

def test_context_injection():
    print("=" * 60)
    print("测试：画布和参考文档信息注入")
    print("=" * 60)
    
    # 1. 创建一个测试画布文档
    print("\n步骤1: 创建测试画布文档...")
    current_engine.load_from_text("关于璧山的批复\n\n测试内容第二段\n第三段内容")
    current_engine.original_path = "test_canvas.docx"
    
    # 2. 添加参考文档（模拟）
    print("步骤2: 模拟添加参考文档...")
    # 注意：这里只是模拟结构，实际使用中需要真实文档
    current_engine.reference_docs = [
        {
            'filename': '请示文件.docx',
            'type': 'docx',
            'doc': current_engine.doc  # 使用相同文档作为示例
        },
        {
            'filename': '批复模板.docx',
            'type': 'docx',
            'doc': current_engine.doc
        }
    ]
    
    # 3. 创建AgentEngine并测试
    print("\n步骤3: 创建AgentEngine实例...")
    service = SmartFillerService()
    agent = AgentEngine(service)
    
    # 4. 调用信息获取方法
    print("\n步骤4: 测试信息获取方法...\n")
    
    canvas_info = agent._get_canvas_info()
    print("【画布文档信息】")
    print(canvas_info)
    print()
    
    ref_docs_info = agent._get_reference_docs_info()
    print("【参考文档信息】")
    print(ref_docs_info)
    print()
    
    # 5. 验证System Prompt构建（模拟run方法的部分逻辑）
    print("\n步骤5: 验证System Prompt构建...\n")
    
    from features.smart_filler.prompts import SYSTEM_PROMPT_OLD_YANG
    import json
    
    plan_str = json.dumps([
        {"step": 1, "description": "测试步骤", "tool_hint": "read_source_content"}
    ], indent=2, ensure_ascii=False)
    
    context_injection = f"""
【运行时上下文】
{canvas_info}

{ref_docs_info}

⚠️ 重要提醒：
- 你的修改操作必须针对【当前画布文档】(通过 `doc` 变量访问)
- 参考文档仅供读取，不可修改
- 当用户说"修改"或"填入"时，是指把参考文档的信息填入画布文档
"""
    
    system_prompt_with_plan = f"{SYSTEM_PROMPT_OLD_YANG}\n\n{context_injection}\n\n[Current Plan]\n{plan_str}\n\nPlease execution the plan step by step."
    
    print("【System Prompt预览】(前800字符)")
    print(system_prompt_with_plan[:800])
    print("\n...[省略剩余部分]...\n")
    
    # 6. 检查关键信息是否存在
    print("步骤6: 检查关键信息...")
    checks = [
        ("画布文件名", "test_canvas.docx" in system_prompt_with_plan),
        ("画布段落数", "段落总数: 3" in system_prompt_with_plan),
        ("参考文档1", "请示文件.docx" in system_prompt_with_plan),
        ("参考文档2", "批复模板.docx" in system_prompt_with_plan),
        ("重要提醒", "⚠️ 重要提醒" in system_prompt_with_plan),
    ]
    
    all_passed = True
    for check_name, check_result in checks:
        status = "✓ 通过" if check_result else "✗ 失败"
        print(f"  {status}: {check_name}")
        if not check_result:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有测试通过！")
    else:
        print("❌ 部分测试失败，请检查代码。")
    print("=" * 60)
    
    return all_passed

if __name__ == "__main__":
    try:
        success = test_context_injection()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试执行出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
