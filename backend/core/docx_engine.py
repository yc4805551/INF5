import json
import io
from docx import Document
from docx.text.paragraph import Paragraph
from typing import List, Dict, Any

class DocxEngine:
    def __init__(self):
        self.doc = None
        self.original_path = None

    def load_document(self, file_stream):
        self.doc = Document(file_stream)
        self.original_path = None
        return self.doc
import json
import io
from docx import Document
from docx.text.paragraph import Paragraph
from docx.shared import RGBColor
from typing import List, Dict, Any, Optional
from .markdown_utils import apply_markdown_to_paragraph
import logging

import os

# Configure logging
log_path = os.getenv("LOG_PATH", "docx_engine_debug.log")
if not os.path.isabs(log_path):
    # If relative, put it in the current working directory or a specific logs dir
    # For now, let's keep it relative to CWD to avoid breaking changes, but use os.path.join if we wanted a subdir
    pass

logging.basicConfig(filename=log_path, level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

class DocxEngine:
    def __init__(self):
        self.doc = None
        self.staging_doc = None # Temporary document for previews
        self.original_path = None

    def load_document(self, file_stream):
        self.doc = Document(file_stream)
        self.staging_doc = None
        return self.doc

    def load_from_path(self, path: str):
        """
        Loads a document from a local file path.
        """
        with open(path, "rb") as f:
            self.doc = Document(f)
        self.original_path = path
        self.staging_doc = None
        return self.doc

    def save_to_path(self, path: str):
        """
        Saves the current document to a local file path.
        """
        target_doc = self.staging_doc if self.staging_doc else self.doc
        if target_doc:
            target_doc.save(path)
            return True
        return False

    def get_preview_data(self) -> List[Dict[str, Any]]:
        """
        Extracts paragraphs to send to frontend for preview.
        Returns a list of paragraphs, each containing a list of runs with formatting.
        """
        # Use staging doc if it exists, otherwise the committed doc
        target_doc = self.staging_doc if self.staging_doc else self.doc
        
        if not target_doc:
            return []
        
        preview_data = []
        for i, para in enumerate(target_doc.paragraphs):
            runs_data = []
            for run in para.runs:
                # Extract color as hex string if exists
                color = None
                if run.font.color and run.font.color.rgb:
                    color = f"#{run.font.color.rgb}"
                
                runs_data.append({
                    "text": run.text,
                    "bold": bool(run.bold),
                    "italic": bool(run.italic),
                    "underline": bool(run.underline),
                    "color": color,
                    "fontSize": run.font.size.pt if run.font.size else None
                })

            preview_data.append({
                "id": i,
                "text": para.text, # Keep raw text for easy reading/debugging
                "style": para.style.name if para.style else "Normal",
                "runs": runs_data
            })
        return preview_data

    def create_staging_copy(self):
        """
        Creates a deep copy of the current document for staging.
        We do this by saving to a memory stream and reloading.
        """
        if not self.doc:
            return
        
        stream = io.BytesIO()
        self.doc.save(stream)
        stream.seek(0)
        self.staging_doc = Document(stream)

    def commit_staging(self):
        """
        Makes the staging document the permanent one.
        """
        if self.staging_doc:
            self.doc = self.staging_doc
            self.staging_doc = None
            return True
        return False

    def discard_staging(self):
        """
        Discards the staging document.
        """
        self.staging_doc = None
        return True

    def apply_patch(self, patch_json: List[Dict[str, Any]], use_staging: bool = False) -> bool:
        """
        Applies a list of surgical edits.
        """
        target_doc = self.staging_doc if use_staging else self.doc
        
        if not target_doc:
            return False

        for op in patch_json:
            op_type = op.get("op")
            if op_type == "replace_text":
                self._replace_paragraph_text(target_doc, op.get("target_id"), op.get("new_text"))
            elif op_type == "search_replace":
                self._search_replace(target_doc, op.get("target_id"), op.get("find_text"), op.get("replace_text"))
            # Future: Add insert_paragraph, delete_paragraph, etc.
        
        return True

    def execute_code(self, code: str) -> bool:
        """
        Executes the provided Python code on the document.
        The code has access to 'doc' (the Document object) and 'docx' (the module).
        """
        target_doc = self.staging_doc if self.staging_doc else self.doc
        if not target_doc:
            return False, "No document loaded"

        # Define the execution context
        # Common imports for docx manipulation
        from docx.shared import Pt, Inches, Cm, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml.ns import qn
        import re

        local_scope = {
            "doc": target_doc,
            "Document": Document,
            "Paragraph": Paragraph,
            "RGBColor": RGBColor,
            "Pt": Pt,
            "Inches": Inches,
            "Cm": Cm,
            "WD_ALIGN_PARAGRAPH": WD_ALIGN_PARAGRAPH,
            "qn": qn,
            "re": re,
            "print": print,
            "smart_replace": self.smart_replace, # Expose helper
            "flexible_replace": self.flexible_replace, # Expose helper
            "search_replace": self.search_replace, # Expose new helper
            "apply_markdown": self.replace_with_markdown, # Expose new helper
            "set_east_asian_font": self.set_east_asian_font # Expose new helper
        }
        
        try:
            exec(code, local_scope)
            return True, ""
        except Exception as e:
            error_msg = f"Error executing code: {str(e)}"
            logging.error(error_msg)
            return False, error_msg

    def flexible_replace(self, doc, find_text: str, replace_text: str) -> bool:
        """
        Tries smart_replace first (preserving formatting).
        If that fails to find/replace anything, falls back to raw text replacement (prioritizing content).
        """
        if not find_text:
            logging.warning("flexible_replace called with empty find_text")
            return False

        logging.info(f"flexible_replace: find='{find_text[:50]}...', replace='{replace_text[:50]}...'")

        # 1. Try smart replace
        if self.smart_replace(doc, find_text, replace_text):
            logging.info("flexible_replace: smart_replace succeeded")
            return True
        
        logging.info("flexible_replace: smart_replace failed, trying raw replace")
        
        # 2. Fallback: Raw text replacement
        # This might lose formatting for the specific paragraph, but ensures content is updated.
        replaced = False
        for para in doc.paragraphs:
            if find_text in para.text:
                # Direct assignment to para.text clears runs and sets new text
                try:
                    para.text = para.text.replace(find_text, replace_text)
                    replaced = True
                    logging.info(f"flexible_replace: raw replace succeeded in paragraph {i}")
                except Exception as e:
                    logging.error(f"flexible_replace: raw replace failed: {e}")
        
        if not replaced:
            logging.warning("flexible_replace: text not found in any paragraph")
            
        return replaced

    def smart_replace(self, doc, find_text: str, replace_text: str) -> bool:
        """
        Replaces text while trying to preserve formatting.
        Handles cases where text is split across runs.
        Strategy: Find the span of runs, replace text in the first run, clear others.
        """
        replaced = False
        for para in doc.paragraphs:
            if find_text in para.text:
                # Naive check: if it's in one run, just do it
                replaced = False
                for run in para.runs:
                    if find_text in run.text:
                        run.text = run.text.replace(find_text, replace_text)
                        replaced = True
                        break
                
                if replaced:
                    continue
                
                # Complex check: Text is split across runs
                # This is a hard problem to solve perfectly without a proper interval tree or character map.
                # Simplified approach:
                # 1. Build a map of character indices to run indices.
                # 2. Find start/end char index of the match.
                # 3. Identify start/end runs.
                
                text = para.text
                start_index = text.find(find_text)
                if start_index == -1:
                    continue
                    
                end_index = start_index + len(find_text)
                
                # Map chars to runs
                current_pos = 0
                start_run_idx = -1
                end_run_idx = -1
                
                for i, run in enumerate(para.runs):
                    run_len = len(run.text)
                    run_end = current_pos + run_len
                    
                    if start_run_idx == -1 and start_index < run_end:
                        start_run_idx = i
                        # Calculate offset in this run
                        start_offset = start_index - current_pos
                    
                    if end_run_idx == -1 and end_index <= run_end:
                        end_run_idx = i
                        end_offset = end_index - current_pos
                        break
                    
                    current_pos += run_len
                
                if start_run_idx != -1 and end_run_idx != -1:
                    # We found the span
                    # Run[start_run_idx] ... Run[end_run_idx]
                    
                    # 1. Update Start Run
                    # We want to keep: prefix + replacement + suffix (if end run is same)
                    # But if end run is different, we keep prefix + replacement.
                    
                    start_run = para.runs[start_run_idx]
                    prefix = start_run.text[:start_index - (current_pos - len(start_run.text) if start_run_idx == end_run_idx else self._get_run_start_pos(para, start_run_idx))]
                    # Wait, calculating offsets again is messy.
                    
                    # Let's use the simpler logic:
                    # Reconstruct the text of the start run to include the replacement.
                    # Clear the text of intermediate runs.
                    # Adjust the text of the end run to keep the suffix.
                    
                    # Re-calculate offsets properly
                    curr = 0
                    for j in range(start_run_idx):
                        curr += len(para.runs[j].text)
                    
                    start_offset_in_run = start_index - curr
                    
                    curr = 0
                    for j in range(end_run_idx):
                        curr += len(para.runs[j].text)
                    end_offset_in_run = end_index - curr
                    
                    if start_run_idx == end_run_idx:
                        # Same run (handled by naive loop usually, but maybe not if multiple occurrences?)
                        run = para.runs[start_run_idx]
                        run.text = run.text[:start_offset_in_run] + replace_text + run.text[end_offset_in_run:]
                    else:
                        # Multi-run
                        # Start run: keep prefix + replace_text
                        para.runs[start_run_idx].text = para.runs[start_run_idx].text[:start_offset_in_run] + replace_text
                        
                        # Middle runs: clear
                        for k in range(start_run_idx + 1, end_run_idx):
                            para.runs[k].text = ""
                            
                        # End run: keep suffix
                        para.runs[end_run_idx].text = para.runs[end_run_idx].text[end_offset_in_run:]
                        replaced = True
        
        return replaced

    def _get_run_start_pos(self, para, run_idx):
        pos = 0
        for i in range(run_idx):
            pos += len(para.runs[i].text)
        return pos

    def _replace_paragraph_text(self, doc, index: int, new_text: str):
        # Deprecated in favor of execute_code, but kept for compatibility if needed
        pass

    def search_replace(self, doc, find_text: str, replace_text: str) -> bool:
        """
        Robust search and replace that handles multiple occurrences and preserves formatting.
        """
        changed_any = False
        for para in doc.paragraphs:
            if find_text not in para.text:
                continue
                
            # Loop until no more matches in this paragraph
            # We need to be careful about infinite loops if replace_text contains find_text
            # But usually we just process the paragraph once or iteratively.
            # Since modifying runs changes indices, it's safer to restart the search in the paragraph after a modification,
            # OR use a while loop.
            
            # Simple safety: limit iterations per paragraph
            iterations = 0
            while find_text in para.text and iterations < 20:
                # Try to find and replace ONE occurrence
                replaced = self._smart_replace_single(para, find_text, replace_text)
                if replaced:
                    changed_any = True
                    iterations += 1
                else:
                    # If text is there but we failed to replace it (e.g. complex split?), break to avoid infinite loop
                    # Or maybe fall back to raw replacement for just this paragraph?
                    # Let's try to be robust.
                    break
        return changed_any

    def _smart_replace_single(self, para, find_text: str, replace_text: str) -> bool:
        """
        Helper to replace the FIRST occurrence of find_text in a paragraph.
        Returns True if replaced.
        """
        # 1. Naive check: if it's in one run
        for run in para.runs:
            if find_text in run.text:
                run.text = run.text.replace(find_text, replace_text, 1)
                return True
        
        # 2. Split across runs
        text = para.text
        start_index = text.find(find_text)
        if start_index == -1:
            return False
            
        end_index = start_index + len(find_text)
        
        # Map chars to runs
        current_pos = 0
        start_run_idx = -1
        end_run_idx = -1
        
        for i, run in enumerate(para.runs):
            run_len = len(run.text)
            run_end = current_pos + run_len
            
            if start_run_idx == -1 and start_index < run_end:
                start_run_idx = i
                # Calculate offset in this run
                # start_offset = start_index - current_pos
            
            if end_run_idx == -1 and end_index <= run_end:
                end_run_idx = i
                # end_offset = end_index - current_pos
                break
            
            current_pos += run_len
        
        if start_run_idx != -1 and end_run_idx != -1:
            # Calculate offsets
            curr = 0
            for j in range(start_run_idx):
                curr += len(para.runs[j].text)
            start_offset_in_run = start_index - curr
            
            curr = 0
            for j in range(end_run_idx):
                curr += len(para.runs[j].text)
            end_offset_in_run = end_index - curr
            
            if start_run_idx == end_run_idx:
                # Same run (handled by naive loop usually)
                run = para.runs[start_run_idx]
                run.text = run.text[:start_offset_in_run] + replace_text + run.text[end_offset_in_run:]
            else:
                # Multi-run
                # Start run: keep prefix + replace_text
                para.runs[start_run_idx].text = para.runs[start_run_idx].text[:start_offset_in_run] + replace_text
                
                # Middle runs: clear
                for k in range(start_run_idx + 1, end_run_idx):
                    para.runs[k].text = ""
                    
                # End run: keep suffix
                para.runs[end_run_idx].text = para.runs[end_run_idx].text[end_offset_in_run:]
            
            return True
            
        return False

    def _search_replace(self, doc, target_id: int, find_text: str, replace_text: str):
        # Deprecated
        pass

    def replace_with_markdown(self, doc, target_index: int, markdown_text: str) -> bool:
        """
        Replaces the content of a paragraph with new markdown text, applying formatting.
        """
        if target_index < 0 or target_index >= len(doc.paragraphs):
            return False
            
        para = doc.paragraphs[target_index]
        logging.info(f"apply_markdown: applying to paragraph {target_index}")
        apply_markdown_to_paragraph(para, markdown_text)
        return True

    def set_east_asian_font(self, run, font_name):
        """
        Safely sets the East Asian font for a run.
        """
        from docx.oxml.ns import qn
        run.font.name = font_name
        run._element.rPr.rFonts.set(qn('w:eastAsia'), font_name)


    def save_to_stream(self):
        stream = io.BytesIO()
        self.doc.save(stream)
        stream.seek(0)
        return stream
