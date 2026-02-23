
def _format_url(target_url):
    """Robust OpenAI-compatible endpoint formatter"""
    if not target_url:
        return ""
    url = target_url.rstrip('/')
    if not url.endswith('/chat/completions'):
        if not url.endswith('/v1'):
            url = f"{url}/v1"
        url = f"{url}/chat/completions"
    return url

providers = ["Gemini", "OpenAI", "DeepSeek", "Ali"]
test_cases = [
    # Base URL without /v1
    ("https://api.openai.com", "https://api.openai.com/v1/chat/completions"),
    # Base URL with /v1
    ("https://api.openai.com/v1", "https://api.openai.com/v1/chat/completions"),
    # Full URL
    ("https://api.openai.com/v1/chat/completions", "https://api.openai.com/v1/chat/completions"),
    # DashScope compatible-mode case
    ("https://dashscope.aliyuncs.com/compatible-mode", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"),
    ("https://dashscope.aliyuncs.com/compatible-mode/v1", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"),
    # DeepSeek case
    ("https://api.deepseek.com", "https://api.deepseek.com/v1/chat/completions"),
]

passed = True
for input_url, expected in test_cases:
    actual = _format_url(input_url)
    if actual == expected:
        print(f"PASS: {input_url} -> {actual}")
    else:
        print(f"FAIL: {input_url}")
        print(f"  Expected: {expected}")
        print(f"  Actual:   {actual}")
        passed = False

if passed:
    print("\nAll multi-provider URL test cases passed!")
else:
    print("\nSome test cases failed.")
    exit(1)
