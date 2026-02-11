
import os

# Dual Model Configuration

# 1. OCR Model (Backend Default)
# Priorities: Environment Variable > Hardcoded Default (DeepSeek)
# This model is used EXCLUSIVELY for Image/PDF-Scan processing.
OCR_MODEL_PROVIDER = os.getenv("OCR_MODEL_PROVIDER", "deepseek") 
OCR_MODEL_NAME = os.getenv("OCR_MODEL_NAME", "deepseek-chat") 
OCR_API_KEY = os.getenv("OCR_API_KEY") or os.getenv("DEEPSEEK_API_KEY") 

# 2. Cleaning Model (Global)
# This is determined dynamically from the frontend request (user selection).
# No hardcoded default here, we rely on the `model_config` passed from the frontend.
