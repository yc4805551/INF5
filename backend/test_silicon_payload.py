import requests
import json

url = "https://api.siliconflow.cn/v1/chat/completions"
# Using a 1x1 dummy transparent PNG base64
b64_img = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

payload3 = {
    "model": "PaddlePaddle/PaddleOCR-VL-1.5",
    "messages": [
        {
            "role": "user",
            "content": [
                {"type": "image", "image_url": {"url": b64_img}},
                {"type": "text", "text": "test"}
            ]
        }
    ]
}

payload4 = {
    "model": "deepseek-ai/DeepSeek-V3", # Or any model
    "messages": [
        {
            "role": "user",
            "content": f"<image>\n{b64_img}\ntest"
        }
    ]
}

headers = {
    "Authorization": "Bearer sk-vzwkfghdwixydzxqjtqfxxfxmmsgwqhbsuouiimxattnzmtf",
    "Content-Type": "application/json"
}

r3 = requests.post(url, json=payload3, headers=headers)
print("Type image test result:", r3.status_code, r3.text)

r4 = requests.post(url, json=payload4, headers=headers)
print("String test result:", r4.status_code, r4.text)
