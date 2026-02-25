import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from features.smart_file_agent.services import SmartFileAgent
import base64
from PIL import Image
import io

agent = SmartFileAgent(ocr_provider="siliconflow")

# Create a huge 4000x4000 dummy image to represent a 300DPI scanned A4 page
print("Creating dummy 4K image...")
img = Image.new('RGB', (4000, 4000), color='white')
buffered = io.BytesIO()
img.save(buffered, format="PNG")
huge_image_bytes = buffered.getvalue()

print(f"Original size: {len(huge_image_bytes)} bytes")

print("Testing resize...")
result_b64 = agent._resize_image_for_vision(huge_image_bytes)
print(f"Resized base64 string length: {len(result_b64)} characters")

# verify it decodes
try:
    header, encoded = result_b64.split(",", 1)
    data = base64.b64decode(encoded)
    res_img = Image.open(io.BytesIO(data))
    print(f"Resulting image dimensions: {res_img.size}")
except Exception as e:
    print("Error decoding result:", e)
    sys.exit(1)
