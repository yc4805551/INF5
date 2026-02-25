import requests
import json
import base64
from PIL import Image
import io

url = "https://api.siliconflow.cn/v1/chat/completions"
headers = {
    "Authorization": "Bearer sk-vzwkfghdwixydzxqjtqfxxfxmmsgwqhbsuouiimxattnzmtf",
    "Content-Type": "application/json"
}

# Create a real 200x200 red image to avoid 1x1 tensor errors
img = Image.new('RGB', (200, 200), color = 'red')
buffered = io.BytesIO()
img.save(buffered, format="JPEG")
b64_img = "data:image/jpeg;base64," + base64.b64encode(buffered.getvalue()).decode()

payload = {
    "model": "PaddlePaddle/PaddleOCR-VL-1.5",
    "messages": [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What is this?"},
                {"type": "image_url", "image_url": {"url": b64_img}}
            ]
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
