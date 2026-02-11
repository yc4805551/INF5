
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
from .config import OCR_MODEL_PROVIDER, OCR_MODEL_NAME, OCR_API_KEY

logger = logging.getLogger(__name__)

class SmartFileAgent:
    def __init__(self, use_llm_clean=False, cleaning_model_config=None):
        self.use_llm_clean = use_llm_clean
        self.cleaning_model_config = cleaning_model_config
        self.merged_buffer = []
        # Initialize OCR Engine independently
        self.ocr_engine = LLMEngine(api_key=OCR_API_KEY)

    def process_files(self, files):
        """
        Generator function to yield progress logs and final result.
        """
        total_files = len(files)
        # Sort files by name to ensure consistent order
        files.sort(key=lambda x: x.filename)
        
        yield json.dumps({"type": "log", "message": f"Found {total_files} files to process..."}) + "\n"

        for index, file in enumerate(files):
            file_name = file.filename
            yield json.dumps({"type": "log", "message": f"Processing [{index+1}/{total_files}]: {file_name}..."}) + "\n"
            
            temp_file_path = None
            try:
                # OPTIMIZATION: Use tempfile to avoid holding large files in RAM
                # unexpected EOF if we read stream? Flask FileStorage.save() is efficient.
                fd, temp_file_path = tempfile.mkstemp()
                os.close(fd) # Close file descriptor, we just need path
                file.save(temp_file_path)
                
                # 2. Route Processing (Pass PATH or Stream from Disk)
                processed_text = ""
                ext = os.path.splitext(file_name)[1].lower()

                if ext in ['.xlsx', '.xls']:
                    processed_text = self._process_excel(temp_file_path)
                elif ext == '.docx':
                    processed_text = self._process_word(temp_file_path)
                elif ext == '.pdf':
                     processed_text = self._process_pdf(temp_file_path)
                     # If text is too short, process as images (OCR)
                     if len(processed_text) < 50:
                         yield json.dumps({"type": "log", "message": f"  - [{file_name}] text content too short, switching to OCR..."}) + "\n"
                         processed_text = self._process_pdf_as_images(temp_file_path)

                elif ext in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']:
                     yield json.dumps({"type": "log", "message": f"  - [{file_name}] Identifying image with {OCR_MODEL_NAME}..."}) + "\n"
                     processed_text = self._process_image(temp_file_path)
                elif ext in ['.txt', '.md', '.csv']:
                    with open(temp_file_path, 'rb') as f:
                        content = f.read()
                        try:
                            processed_text = content.decode('utf-8')
                        except UnicodeDecodeError:
                            processed_text = content.decode('gbk', errors='ignore')

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
            finally:
                # Cleanup Temp File
                if temp_file_path and os.path.exists(temp_file_path):
                    try:
                        os.remove(temp_file_path)
                    except:
                        pass

        # 4. Merger
        yield json.dumps({"type": "log", "message": "Merging results..."}) + "\n"
        full_text = "".join(self.merged_buffer)

        # 5. Optional: LLM Cleaning
        if self.use_llm_clean and self.cleaning_model_config:
             pass

        # Final Yield
        yield json.dumps({"type": "result", "text": full_text}) + "\n"
        yield json.dumps({"type": "log", "message": "Done."}) + "\n"

    def _process_excel(self, file_path):
        try:
            # pandas read_excel supports path
            df = pd.read_excel(file_path)
            return df.to_markdown(index=False)
        except Exception as e:
            return f"[Excel Error: {str(e)}]"

    def _process_word(self, file_path):
        try:
            # python-docx supports path
            doc = Document(file_path)
            full_text = []
            for para in doc.paragraphs:
                full_text.append(para.text)
            return "\n".join(full_text)
        except Exception as e:
            return f"[Word Error: {str(e)}]"

    def _process_pdf(self, file_path):
        try:
            # fitz.open supports path
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        except Exception as e:
            logger.error(f"PDF Error: {e}")
            return "" 

    def _process_pdf_as_images(self, file_path):
        try:
            doc = fitz.open(file_path)
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

    def _process_image(self, file_path):
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            import base64
            b64_img = "data:image/png;base64," + base64.b64encode(content).decode('utf-8')
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
            "Authorization": f"Bearer {OCR_API_KEY}"
        }
        
        payload = {
            "model": OCR_MODEL_NAME,
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
        
        from core.llm_config import get_llm_config_manager
        config_manager = get_llm_config_manager()
        provider_config = config_manager.get_provider_config(OCR_MODEL_PROVIDER)
        endpoint = provider_config.get("endpoint")
        
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
