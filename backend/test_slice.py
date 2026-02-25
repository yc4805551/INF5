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

print(f"Original file size: {len(huge_image_bytes)} bytes")

print("Testing slice and OCR method (we mock _call_vision_api to just return slice info)...")

# Mock the API call so we don't actually hit Siliconflow 4 times for a white image
def mock_call_vision_api(b64, prompt):
    print(f"  -> Called vision API with image length {len(b64)}")
    return "[OCR RESULT...]"
    
agent._call_vision_api = mock_call_vision_api

result = agent._slice_and_ocr_image(huge_image_bytes, "Test prompt")
print("\nFinal Result:")
print(result)
