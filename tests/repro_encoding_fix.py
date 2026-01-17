import json
import logging

# Mock Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def log_debug(msg):
    print(f"[DEBUG] {msg}")

# Mock Tool Logic (extracted from tools.py)
def execute_document_script_mock(kwargs):
    script_code = kwargs.get("script_code") or kwargs.get("code")
    
    if not script_code and "raw_input" in kwargs:
        # Fallback: Try to parse from raw_input string if it looks like JSON
        import json
        try:
            log_debug(f"Raw Input: {kwargs['raw_input'][:50]}...")
            data = json.loads(kwargs["raw_input"])
            script_code = data.get("script_code") or data.get("code")
        except:
            # If JSON parsing fails (common with LLM multiline strings), try Regex extraction
            import re
            match = re.search(r'[\'"](?:script_code|code)[\'"]\s*:\s*[\'"]((?:[^"\\]|\\.)*)[\'"]', kwargs["raw_input"], re.DOTALL)
            if match:
                # Unescape the captured string
                try:
                    # CURRENT BUGGY IMPLEMENTATION
                    script_code = match.group(1).encode('utf-8').decode('unicode_escape')
                except:
                    script_code = match.group(1)
            else:
                script_code = kwargs["raw_input"]

    return script_code

# Test Case
if __name__ == "__main__":
    # Simulate a malformed JSON input often seen from LLMs where they use single quotes or unescaped newlines inside
    # "Target": We want to see if Chinese text gets preserved or mangled.
    
    # Case 1: Regex Extraction Path (The buggy path)
    # LLM might output something that fails json.loads but hits the regex
    raw_input_1 = """
    {
        'script_code': 'print("用户指令: 编写批复")'
    }
    """
    
    print("--- Test Case 1: Regex Extraction (Bug Repro) ---")
    result_1 = execute_document_script_mock({"raw_input": raw_input_1})
    print(f"Result: {result_1}")
    
    expected_substring = "用户指令"
    if expected_substring in result_1:
         # Wait, if it IS buggy, does it mangle '用户'?
         # '用户'.encode('utf-8') -> b'\xe7\x94\xa8\xe6\x88\xb7'
         # .decode('unicode_escape') -> treated as literal characters unless it sees \x?? 
         # Actually unicode_escape decodes \uXXXX. 
         # But if the string contains actual UTF-8 bytes perceived as a string... 
         # The issue reported is "Mojibake".
         # Let's see what happens.
         pass
    else:
         print("WARN: '用户指令' not found, might be mangled.")
         
    # Case 2: Simple Chinese Test directly
    # '中' is \xe4\xb8\xad in utf-8. 
    # If we take that str '中' and do .encode('utf-8') we get bytes b'\xe4\xb8\xad'.
    # If we .decode('unicode_escape') on those bytes...
    # unicode_escape treats bytes as ASCII chars mostly, but handles \x and \u.
    # b'\xe4' is latin-1 char 'ä'.
    
    s = "中文"
    try:
        mangled = s.encode('utf-8').decode('unicode_escape')
        print(f"\nDirect Test: '{s}' -> '{mangled}'")
        if s != mangled:
            print("Confirmed: Encoding Logic mangles UTF-8 characters.")
    except Exception as e:
        print(f"Direct Test Error: {e}")
