import requests
import base64
import json

img_path = r"C:\Users\Administrator\.gemini\antigravity\brain\f699a2c6-cd0d-4f6d-bf71-2f115300020f\media__1772040025094.png"
with open(img_path, "rb") as f:
    img_b64 = base64.b64encode(f.read()).decode("utf-8")

b64_img = "data:image/png;base64," + img_b64

prompt = (
    "你是一个专业的中文文档和表格排版专家。请将图片中的内容精准地转换为 Markdown 格式。\n"
    "要求：\n"
    "1. 请修正可能由于扫描造成的错别字或折叠。\n"
    "2. 如果图片中包含表格，请务必使用标准的 Markdown 表格语法 ('|---|') 进行严谨的还原，不要漏掉合并单元格或表头。\n"
    "3. 不要输出任何开场白或解释文字，直接输出转换后的 Markdown。\n"
    "4. 如果图片内容完全无法辨认、或者包含大量无意义的乱码和符号，请直接输出 '[UNREADABLE]'，不要强行编造或输出乱码。"
)

# Test with deepseek-vl2 (assuming user switched to deepseek)
payload = {
    "model": "deepseek-ai/deepseek-vl2",
    "messages": [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": b64_img}}
            ]
        }
    ],
    "max_tokens": 2048,
    "temperature": 0.0,
    "top_p": 0.1
}

headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer sk-vzwkfghdwixydzxqjtqfxxfxmmsgwqhbsuouiimxattnzmtf"
}

print("Requesting DeepSeek-VL2 with temp=0.0...")
res = requests.post("https://api.siliconflow.cn/v1/chat/completions", json=payload, headers=headers)
print("Response Status:", res.status_code)
if res.status_code == 200:
    print(res.json()["choices"][0]["message"]["content"])
else:
    print(res.text)
