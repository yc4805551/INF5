import json
import ast
import logging

# Mock Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def log_debug(msg):
    print(f"[DEBUG] {msg}")

# FIXED Tool Logic
def execute_document_script_fixed(kwargs):
    script_code = kwargs.get("script_code") or kwargs.get("code")
    
    if not script_code and "raw_input" in kwargs:
        # Fallback: Try to parse from raw_input string if it looks like JSON
        import json
        import ast
        try:
            log_debug(f"Raw Input: {kwargs['raw_input'][:50]}...")
            data = json.loads(kwargs["raw_input"])
            script_code = data.get("script_code") or data.get("code")
        except:
            # If JSON parsing fails, try Regex extraction
            import re
            match = re.search(r'[\'"](?:script_code|code)[\'"]\s*:\s*[\'"]((?:[^"\\]|\\.)*)[\'"]', kwargs["raw_input"], re.DOTALL)
            if match:
                # FIXED: Use ast.literal_eval to safely unescape
                captured = match.group(1)
                try:
                    script_code = ast.literal_eval(f'"{captured}"')
                except:
                    # Fallback to simple replacements
                    try:
                        script_code = captured.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r').replace('\\"', '"').replace("\\'", "'").replace('\\\\', '\\')
                    except:
                        script_code = captured
            else:
                script_code = kwargs["raw_input"]

    return script_code

# Test Cases
if __name__ == "__main__":
    print("=== 编码修复验证测试 ===\n")
    
    # Test 1: Regex path with Chinese characters
    raw_input_1 = """
    {
        'script_code': 'print("用户指令: 编写批复\\n经审核同意")'
    }
    """
    
    print("测试 1: 正则提取路径（包含中文）")
    result_1 = execute_document_script_fixed({"raw_input": raw_input_1})
    print(f"结果: {result_1}")
    
    # Verify Chinese characters are preserved
    if "用户指令" in result_1 and "经审核" in result_1:
        print("✓ 通过: 中文字符保留完整\n")
    else:
        print("✗ 失败: 中文字符损坏\n")
    
    # Test 2: Direct string with newlines
    raw_input_2 = """{"script_code": "for p in doc.paragraphs:\\n    if '标题' in p.text:\\n        print('找到标题')"}"""
    
    print("测试 2: JSON 格式（包含转义字符）")
    result_2 = execute_document_script_fixed({"raw_input": raw_input_2})
    print(f"结果: {result_2}")
    
    if '\n' in result_2 and '标题' in result_2:
        print("✓ 通过: 换行符正常转换，中文保留\n")
    else:
        print("✗ 失败: 转义处理有问题\n")
    
    # Test 3: Complex mixed content
    raw_input_3 = """{'code': '# 添加段落\\nfor i in range(5):\\n    doc.add_paragraph(f"第{i+1}项：重要内容")'}"""
    
    print("测试 3: 复杂混合内容")
    result_3 = execute_document_script_fixed({"raw_input": raw_input_3})
    print(f"结果: {result_3}")
    
    if '第' in result_3 and '项' in result_3 and '\n' in result_3:
        print("✓ 通过: 复杂内容处理正确\n")
    else:
        print("✗ 失败: 复杂内容处理有误\n")
        
    print("=== 测试完成 ===")
