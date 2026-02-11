
import os
import io
import json
import logging
import traceback
import tempfile
import pandas as pd
import fitz  # PyMuPDF
from docx import Document
from datetime import datetime
from PIL import Image

# Core LLM Engine for OCR
from core.llm_engine import LLMEngine
from .config import OCR_MODEL_PROVIDER, OCR_MODEL_NAME, OCR_API_KEY, OCR_ENDPOINT

logger = logging.getLogger(__name__)

class SmartFileAgent:
    def __init__(self, use_llm_clean=False, cleaning_model_config=None, ocr_provider=None):
        self.use_llm_clean = use_llm_clean
        self.cleaning_model_config = cleaning_model_config
        self.merged_buffer = []

        # Resolve OCR Configuration
        # Priority 1: Direct OCR_* Env Overrides (Dedicated Mode)
        if OCR_ENDPOINT:
             self.ocr_api_key = OCR_API_KEY
             self.ocr_model_name = OCR_MODEL_NAME
             self.ocr_endpoint = OCR_ENDPOINT
             self.ocr_provider = "custom"
        else:
             # Priority 2: Provider Lookup (via LLMConfigManager)
             self.ocr_provider = ocr_provider or OCR_MODEL_PROVIDER
             
             from core.llm_config import get_llm_config_manager
             cm = get_llm_config_manager()
             provider_config = cm.get_provider_config(self.ocr_provider)

             if self.ocr_provider == OCR_MODEL_PROVIDER:
                 self.ocr_api_key = OCR_API_KEY or provider_config.get("apiKey")
                 self.ocr_model_name = OCR_MODEL_NAME or provider_config.get("model")
             else:
                 self.ocr_api_key = provider_config.get("apiKey")
                 self.ocr_model_name = provider_config.get("model")
             
             self.ocr_endpoint = provider_config.get("endpoint")

        # Initialize OCR Engine independently
        self.ocr_engine = LLMEngine(api_key=self.ocr_api_key)

    def process_files(self, files_data):
        """
        Generator function to yield progress logs and final result.
        files_data: List of dicts {'filename': str, 'content': bytes}
        """
        total_files = len(files_data)
        # Sort files by name to ensure consistent order
        files_data.sort(key=lambda x: x['filename'])
        
        yield json.dumps({"type": "log", "message": f"Found {total_files} files to process..."}) + "\n"
        yield json.dumps({"type": "log", "message": f"Active OCR Configuration: Provider=[{self.ocr_provider}], Model=[{self.ocr_model_name}]"}) + "\n"

        for index, file_info in enumerate(files_data):
            file_name = file_info['filename']
            file_content = file_info['content']
            
            yield json.dumps({"type": "log", "message": f"Processing [{index+1}/{total_files}]: {file_name}..."}) + "\n"
            
            try:
                # Content is already bytes
                file_bytes = io.BytesIO(file_content)
                
                # 2. Route Processing (Pass in-memory BytesIO)
                processed_text = ""
                ext = os.path.splitext(file_name)[1].lower()

                if ext in ['.xlsx', '.xls']:
                    processed_text = self._process_excel(file_bytes)
                elif ext == '.docx':
                    processed_text = self._process_word(file_bytes)
                elif ext == '.pdf':
                     processed_text = self._process_pdf(file_content) # PyMuPDF needs bytes or filename, not BytesIO generally (but fitz.open(stream=...) works)
                     
                     # If text is too short, process as images (OCR)
                     if len(processed_text) < 50:
                         yield json.dumps({"type": "log", "message": f"  - [{file_name}] text content too short, switching to OCR..."}) + "\n"
                         processed_text = self._process_pdf_as_images(file_content)

                elif ext in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']:
                     yield json.dumps({"type": "log", "message": f"  - [{file_name}] Identifying image with {self.ocr_model_name}..."}) + "\n"
                     processed_text = self._process_image(file_content)
                elif ext in ['.txt', '.md', '.csv']:
                    try:
                        processed_text = file_content.decode('utf-8')
                    except UnicodeDecodeError:
                        processed_text = file_content.decode('gbk', errors='ignore')

                else:
                    processed_text = f"[Skipped unsupported file: {file_name}]"

                # 3. Format and Append
                formatted_section = f"\n\n{'='*20}\n文件名: {file_name}\n{'='*20}\n\n{processed_text}"
                self.merged_buffer.append(formatted_section)
                
            except Exception as e:
                error_msg = f"Error processing {file_name}: {str(e)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                yield json.dumps({"type": "log", "message": f"  - [Error] {error_msg}"}) + "\n"
                self.merged_buffer.append(f"\n\n[Error processing {file_name}]\n")

        # 4. Merger
        yield json.dumps({"type": "log", "message": "Merging results..."}) + "\n"
        full_text = "".join(self.merged_buffer)

        # 5. Optional: LLM Cleaning
        if self.use_llm_clean and self.cleaning_model_config:
             pass

        # Final Yield
        yield json.dumps({"type": "result", "text": full_text}) + "\n"
        yield json.dumps({"type": "log", "message": "Done."}) + "\n"

    def _process_excel(self, file_stream):
        try:
            # pandas read_excel supports file-like objects (BytesIO)
            df = pd.read_excel(file_stream)
            return df.to_markdown(index=False)
        except Exception as e:
            return f"[Excel Error: {str(e)}]"

    def _process_word(self, file_stream):
        try:
            # python-docx supports file-like objects (BytesIO)
            doc = Document(file_stream)
            full_text = []
            
            # 1. Extract Paragraphs
            for para in doc.paragraphs:
                if para.text.strip():
                    full_text.append(para.text)
            
            # 2. Extract Tables (Append them to ensure data isn't lost)
            if doc.tables:
                full_text.append("\n\n--- Tables Extracted from Document ---\n")
                for table in doc.tables:
                    # Simple Markdown Table Converter
                    # Get all rows
                    rows = []
                    for row in table.rows:
                        cells = [cell.text.strip().replace('\n', ' ') for cell in row.cells]
                        rows.append(cells)
                    
                    if not rows:
                        continue

                    # Determine columns (max length of any row)
                    # Some merged cells might cause issues, this is a basic approximation
                    num_cols = max(len(r) for r in rows) if rows else 0
                    
                    if num_cols > 0:
                        # 1. Header
                        header = rows[0]
                        # Pad header if needed
                        header += [''] * (num_cols - len(header))
                        full_text.append("| " + " | ".join(header) + " |")
                        
                        # 2. Separator
                        full_text.append("| " + " | ".join(['---'] * num_cols) + " |")
                        
                        # 3. Body
                        for row in rows[1:]:
                            # Pad row if needed
                            row += [''] * (num_cols - len(row))
                            full_text.append("| " + " | ".join(row) + " |")
                        
                        full_text.append("\n") # Spacing between tables

            return "\n".join(full_text)
        except Exception as e:
            return f"[Word Error: {str(e)}]"

    def _process_pdf(self, file_bytes):
        try:
            # fitz.open(stream=..., filetype="pdf")
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        except Exception as e:
            logger.error(f"PDF Error: {e}")
            return "" 

    def _process_pdf_as_images(self, file_bytes):
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            full_ocr_text = []
            
            for i, page in enumerate(doc):
                pix = page.get_pixmap()
                img_data = pix.tobytes("png")
                
                import base64
                b64_img = "data:image/png;base64," + base64.b64encode(img_data).decode('utf-8')
                
                prompt = "Please OCR this image. Output strictly in Markdown format. If there are tables, preserve them as Markdown tables. Do not add introductory text."
                
                vision_response = self._call_vision_api(b64_img, prompt)
                full_ocr_text.append(vision_response)
            
            doc.close()
            return "\n\n".join(full_ocr_text)
        except Exception as e:
            return f"[PDF OCR Error: {e}]"

    def _process_image(self, file_bytes):
        try:
            import base64
            b64_img = "data:image/png;base64," + base64.b64encode(file_bytes).decode('utf-8')
            prompt = "Transcribe this image to Markdown."
            return self._call_vision_api(b64_img, prompt)
        except Exception as e:
            return f"[Image Processing Error: {str(e)}]"

    def _call_vision_api(self, b64_image, prompt):
        # Implementation of OpenAI-compatible Vision request
        # Assuming 'DeepSeek OCR' or 'depOCR' creates an OpenAI-compatible endpoint that accepts image_url
        
        import requests
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.ocr_api_key}"
        }
        
        payload = {
            "model": self.ocr_model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": b64_image
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 4096
        }
        
        # Use pre-resolved endpoint
        endpoint = self.ocr_endpoint
        
        if not endpoint:
            # Fallback if somehow missing (shouldn't happen given __init__ logic)
            return "[Error: No Endpoint Configured for OCR Model]"
        
        if not endpoint:
            return "[Error: No Endpoint Configured for OCR Model]"

        if "/chat/completions" not in endpoint:
             endpoint = endpoint.rstrip("/") + "/chat/completions"

        try:
            response = requests.post(endpoint, headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                res_json = response.json()
                return res_json['choices'][0]['message']['content']
            else:
                return f"[OCR API Error {response.status_code}: {response.text}]"
        except Exception as e:
            return f"[OCR Request Failed: {str(e)}]"
