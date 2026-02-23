
import logging

def format_ali_url(target_url):
    """Replication of the fix in proxies.py"""
    url = target_url.rstrip('/')
    if not url.endswith('/chat/completions'):
        if not url.endswith('/v1'):
            url = f"{url}/v1"
        url = f"{url}/chat/completions"
    return url

test_cases = [
    ("https://dashscope.aliyuncs.com/compatible-mode", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"),
    ("https://dashscope.aliyuncs.com/compatible-mode/", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"),
    ("https://dashscope.aliyuncs.com/compatible-mode/v1", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"),
    ("https://dashscope.aliyuncs.com/compatible-mode/v1/", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"),
    ("https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"),
]

passed = True
for input_url, expected in test_cases:
    actual = format_ali_url(input_url)
    if actual == expected:
        print(f"PASS: {input_url} -> {actual}")
    else:
        print(f"FAIL: {input_url}")
        print(f"  Expected: {expected}")
        print(f"  Actual:   {actual}")
        passed = False

if passed:
    print("\nAll test cases passed!")
else:
    print("\nSome test cases failed.")
    exit(1)
