import sys, os
sys.path.append(os.path.abspath(os.path.dirname("")))
from features.smart_file_agent.services import SmartFileAgent
from PIL import Image

agent = SmartFileAgent(ocr_provider="siliconflow")

img_path = r"C:\Users\Administrator\.gemini\antigravity\brain\f699a2c6-cd0d-4f6d-bf71-2f115300020f\media__1772040025094.png"
with open(img_path, "rb") as f:
    img_bytes = f.read()

prompt = (
    "你是一个专业的中文文档和表格排版专家。请将图片中的内容精准地转换为 Markdown 格式。\n"
    "要求：\n"
    "1. 请修正可能由于扫描造成的错别字或折叠。\n"
    "2. 如果图片中包含表格，请务必使用标准的 Markdown 表格语法 ('|---|') 进行严谨的还原，不要漏掉合并单元格或表头。\n"
    "3. 不要输出任何开场白或解释文字，直接输出转换后的 Markdown。\n"
    "4. 如果图片内容完全无法辨认、或者包含大量无意义的乱码和符号，请直接输出 '[UNREADABLE]'，不要强行编造或输出乱码。"
)

if not os.path.exists(img_path):
    print("Image not found:", img_path)
    sys.exit(1)

# test 1: check if whole image is detected as blank
img = Image.open(img_path)
print("Whole image blank?", agent._is_image_mostly_blank(img))

print("Slicing and OCRing...")
res = agent._slice_and_ocr_image(img_bytes, prompt)
print("\n---Result---\n")
print(res)
print("\n---Ghosts---\n")
res_scrubbed = agent._scrub_ghosts(res)
print(res_scrubbed)
