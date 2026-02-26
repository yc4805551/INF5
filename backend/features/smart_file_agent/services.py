
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
        self.ocr_provider = ocr_provider or OCR_MODEL_PROVIDER
        
        from core.llm_config import get_llm_config_manager
        cm = get_llm_config_manager()
        provider_config = cm.get_provider_config(self.ocr_provider)

        # Priority 1: Direct OCR_* Env Overrides (Dedicated Mode) 
        # Only use these overrides if they are explicitly configured AND we are using the default/env provider
        if OCR_ENDPOINT and self.ocr_provider == OCR_MODEL_PROVIDER and getattr(self, 'use_legacy_ocr', False):
             self.ocr_api_key = OCR_API_KEY
             self.ocr_model_name = OCR_MODEL_NAME
             self.ocr_endpoint = OCR_ENDPOINT
             self.ocr_provider = "custom"
        else:
             # Priority 2: Provider Lookup (via LLMConfigManager)
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
                     processed_text = ""
                     for update in self._process_pdf_smart(file_content, file_name):
                         if isinstance(update, dict):
                             processed_text = update.get("text", "")
                         else:
                             yield update
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

    def _process_pdf_smart(self, file_bytes, file_name):
        try:
            import fitz
            import re
            
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            full_ocr_text = []
            
            for i, page in enumerate(doc):
                page_text = page.get_text()
                
                # Heuristic to detect gibberish per page
                non_ws_text = re.sub(r'\s+', '', page_text)
                valid_chars = re.findall(r'[\u4e00-\u9fa5A-Za-z0-9]', non_ws_text)
                chinese_chars = re.findall(r'[\u4e00-\u9fa5]', non_ws_text)
                
                is_gibberish = False
                if len(non_ws_text) > 0:
                    if (len(valid_chars) / len(non_ws_text)) < 0.2:
                        is_gibberish = True
                    elif len(chinese_chars) < 5 and len(valid_chars) > 50:
                        is_gibberish = True
                
                if len(page_text) < 20 or is_gibberish:
                    yield json.dumps({"type": "log", "message": f"  - [{file_name}] 第 {i+1} 页为扫描件或乱码，启动 OCR 引擎..."}) + "\n"
                    # We extract at standard resolution, if it's too big, slicing will handle it.
                    pix = page.get_pixmap()
                    img_data = pix.tobytes("png")
                    
                    prompt = (
                        "你是一个专业的中文文档和表格排版专家。请将图片中的内容精准地转换为 Markdown 格式。\n"
                        "要求：\n"
                        "1. 请修正可能由于扫描造成的错别字或折叠。\n"
                        "2. 如果图片中包含表格，请务必使用标准的 Markdown 表格语法 ('|---|') 进行严谨的还原，不要漏掉合并单元格或表头。\n"
                        "3. 不要输出任何开场白或解释文字，直接输出转换后的 Markdown。\n"
                        "4. 如果图片内容完全无法辨认、或者包含大量无意义的乱码和符号，请直接输出 '[UNREADABLE]'，不要强行编造或输出乱码。"
                    )
                    
                    vision_response = self._slice_and_ocr_image(img_data, prompt)
                    full_ocr_text.append(vision_response)
                else:
                    full_ocr_text.append(page_text)
            
            doc.close()
            yield {"text": "\n\n".join(full_ocr_text)}
        except Exception as e:
            logger.error(f"PDF Error: {e}")
            yield {"text": f"[PDF Extract Error: {e}]"}

    def _scrub_ghosts(self, text):
        import re
        # "[UNREADABLE]" is deliberately removed from this list because it's our requested output for 
        # completely dead spaces. It shouldn't trigger a verbose error message replacing valid text.
        ghost_signatures = ["畜牧兽医", "<|LOC_", "omoData", "阴夜雨", "重夜雨", "لن قم المو", "Employee"]
        if any(ghost in text for ghost in ghost_signatures):
            return "" # Silently drop the hallucinated text
        
        # Scrub generative VLM token loops (e.g. }}}}}}} or 1.1.1.1.1.)
        text = re.sub(r'(\}\s*){5,}', '', text)
        text = re.sub(r'(\{\s*){5,}', '', text)
        text = re.sub(r'(1\.\s*){5,}', '', text)
        text = re.sub(r'(-\s*){10,}', '', text)
        
        # Strip out localized [UNREADABLE] markers so they don't clutter the final markdown
        return text.replace("[UNREADABLE]", "").strip()
    def _is_image_mostly_blank(self, pil_img, min_pixel_threshold=240, max_color_diff=15):
        try:
            from PIL import Image, ImageStat
            # Convert to grayscale to check brightness and variance
            gray = pil_img.convert('L')
            
            # Low-pass filter: resize to a tiny thumbnail using Bilinear interpolation.
            # This completely annihilates microscopic scanner dust/noise (averaging it out to white)
            # but preserves the larger structural gray bands created by actual text.
            tiny = gray.resize((100, 100), Image.Resampling.BILINEAR)
            
            stat = ImageStat.Stat(tiny)
            min_val, max_val = stat.extrema[0]
            
            # If the darkest pixel is very bright white/gray (e.g. >= 240)
            if min_val >= min_pixel_threshold:
                return True
                
            # Or if there is almost no contrast (difference between darkest and lightest pixel is tiny)
            # This catches solid gray/black/colored boxes that have no text or features
            if (max_val - min_val) < max_color_diff:
                return True
                
            return False
        except Exception:
            return False

    def _auto_crop_whitespace(self, pil_img):
        try:
            import numpy as np
            from PIL import Image
            
            # Convert to grayscale to evaluate pixel intensity
            gray = pil_img.convert('L')
            arr = np.array(gray)
            
            # Threshold: pixels darker than 200 are considered 'ink'
            ink_threshold = 200
            
            # Count how many ink pixels are in each row
            ink_pixels_per_row = np.sum(arr < ink_threshold, axis=1)
            
            # A row is considered to have 'text' if it has at least 10 ink pixels 
            # (This ignores single specks of dust, staple marks, or scanner noise)
            text_rows = np.where(ink_pixels_per_row > 10)[0]
            
            if len(text_rows) > 0:
                top = text_rows[0]
                bottom = text_rows[-1]
                
                # Do the same for columns, but only within the y-bounds we just found
                ink_pixels_per_col = np.sum(arr[top:bottom, :] < ink_threshold, axis=0)
                text_cols = np.where(ink_pixels_per_col > 10)[0]
                
                if len(text_cols) > 0:
                    left = text_cols[0]
                    right = text_cols[-1]
                    
                    # Add a comfortable margin of 40 pixels so descenders aren't clipped
                    margin = 40
                    h, w = arr.shape
                    top = max(0, int(top - margin))
                    bottom = min(h, int(bottom + margin))
                    left = max(0, int(left - margin))
                    right = min(w, int(right + margin))
                    
                    # If the cropped area is extremely tiny (like a single smudge), don't crop
                    if (bottom - top) < 50 or (right - left) < 50:
                        return pil_img
                        
                    return pil_img.crop((left, top, right, bottom))
            return pil_img
        except Exception as e:
            return pil_img

    def _slice_and_ocr_image(self, img_bytes, prompt, max_pixels=4000000, max_width=1600):
        try:
            from PIL import Image
            import io
            import base64
            
            img = Image.open(io.BytesIO(img_bytes))
            if img.mode != 'RGB':
                img = img.convert('RGB')
                
            # Smart Auto-Crop: Remove extreme whitespace from document borders (especially the bottom)
            # This absolutely prevents "Prompt Bleeding" / "Instruction Hallucination" from VLMs like PaddleOCR
            img = self._auto_crop_whitespace(img)
                
            orig_width, orig_height = img.size
            # Cap the maximum width to 1600 pixels (very high res) to avoid excessive slice counts on 4K/8K scans
            if orig_width > max_width:
                new_width = max_width
                new_height = int((max_width / orig_width) * orig_height)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
            width, height = img.size
            if width * height <= max_pixels:
                if self._is_image_mostly_blank(img):
                    return "" # Skip entirely blank images before OCR to prevent hallucinations
                
                # Image is small enough, process as usual but convert to PNG to preserve sharp text edges
                # (Generative VLMs often hallucinate on JPEG compression artifacts around text)
                buffered = io.BytesIO()
                img.save(buffered, format="PNG")
                b64_img = "data:image/png;base64," + base64.b64encode(buffered.getvalue()).decode('utf-8')
                return self._scrub_ghosts(self._call_vision_api(b64_img, prompt))
                
            # Image is too large. Slice it horizontally to preserve resolution.
            num_slices = (width * height // max_pixels) + 1
            slice_height = height // num_slices
            
            full_text = []
            for i in range(num_slices):
                top = i * slice_height
                bottom = height if i == num_slices - 1 else (i + 1) * slice_height
                
                # Add a 60-pixel overlap to avoid cutting text lines in half completely
                overlap = 60 if i > 0 else 0
                box = (0, max(0, top - overlap), width, bottom)
                
                slice_img = img.crop(box)
                
                if self._is_image_mostly_blank(slice_img):
                    continue # Skip this slice if it's completely blank
                
                buffered = io.BytesIO()
                slice_img.save(buffered, format="PNG")
                b64_img = "data:image/png;base64," + base64.b64encode(buffered.getvalue()).decode('utf-8')
                
                slice_prompt = prompt
                if num_slices > 1:
                    slice_prompt += f"\n\n（注意：这是超长图的第 {i+1}/{num_slices} 部分截图，请直接输出图里的内容文本，由于可能截断了部分图形不要擅自发散废话。如果由于切片导致本片完全是空白或者乱码，请仅输出 [UNREADABLE]）"
                
                response = self._call_vision_api(b64_img, slice_prompt)
                scrubbed_response = self._scrub_ghosts(response)
                if scrubbed_response:
                    full_text.append(scrubbed_response)
                
            return "\n\n".join(full_text)
        except Exception as e:
            import base64
            import logging
            logging.error(f"Image slice processing error: {e}")
            # Fallback to direct call, hoping for the best
            b64_img = "data:image/png;base64," + base64.b64encode(img_bytes).decode('utf-8')
            return self._scrub_ghosts(self._call_vision_api(b64_img, prompt))



    def _process_image(self, file_bytes):
        try:
            prompt = (
                "你是一个专业的中文文档和表格排版专家。请将图片中的内容精准地转换为 Markdown 格式。\n"
                "要求：\n"
                "1. 请修正可能由于扫描造成的错别字或折叠。\n"
                "2. 如果图片中包含表格，请务必使用标准的 Markdown 表格语法 ('|---|') 进行严谨的还原，不要漏掉合并单元格或表头。\n"
                "3. 不要输出任何开场白或解释文字，直接输出转换后的 Markdown。\n"
                "4. 如果图片内容完全无法辨认、或者包含大量无意义的乱码和符号，请直接输出 '[UNREADABLE]'，不要强行编造或输出乱码。"
            )
            return self._slice_and_ocr_image(file_bytes, prompt)
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
        
        content_payload = [
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {
                    "url": b64_image
                }
            }
        ]

        payload = {
            "model": self.ocr_model_name,
            "messages": [
                {
                    "role": "user",
                    "content": content_payload
                }
            ],
            "max_tokens": 4096,
            "temperature": 0.2, # Slightly > 0 to prevent infinite loops on degenerate inputs
            "top_p": 0.9,
            "presence_penalty": 0.5, # Prevent endless repetition of characters like `}}}}` or `1.1.`
            "frequency_penalty": 0.5
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
            response = requests.post(endpoint, headers=headers, json=payload, timeout=180)
            if response.status_code == 200:
                res_json = response.json()
                return res_json['choices'][0]['message']['content']
            else:
                return f"[OCR API Error {response.status_code}: {response.text}]"
        except Exception as e:
            return f"[OCR Request Failed: {str(e)}]"
