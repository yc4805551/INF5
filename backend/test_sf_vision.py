import requests
import json
import base64

url = "https://api.siliconflow.cn/v1/chat/completions"
b64_img = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

headers = {
    "Authorization": "Bearer sk-vzwkfghdwixydzxqjtqfxxfxmmsgwqhbsuouiimxattnzmtf",
    "Content-Type": "application/json"
}

def test_payload(name, content):
    print(f"\n--- Testing {name} ---")
    payload = {
        "model": "PaddlePaddle/PaddleOCR-VL-1.5",
        "messages": [
            {
                "role": "user",
                "content": content
            }
        ],
        "max_tokens": 1024
    }
    r = requests.post(url, json=payload, headers=headers)
    print(r.status_code)
    try:
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
    except:
        print(r.text)

# 1. Standard OpenAI with image_url array
test_payload("Array with image_url", [
    {"type": "image_url", "image_url": {"url": b64_img}},
    {"type": "text", "text": "What is this?"}
])

# 2. Qwen-VL style with image array
test_payload("Array with image", [
    {"type": "image", "image": b64_img},
    {"type": "text", "text": "What is this?"}
])

# 3. String with <image>
test_payload("String with <image>", f"<image>\n{b64_img}\nWhat is this?")
