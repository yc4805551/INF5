import logging
import json
from typing import Dict, Any, List, Optional
from core.llm_engine import LLMEngine
from core.docx_engine import DocxEngine

logger = logging.getLogger(__name__)

class CanvasAgent:
    def __init__(self, llm: LLMEngine, doc_engine: DocxEngine):
        self.llm = llm
        self.doc_engine = doc_engine
        self.max_retries = 2  # Speed optimizations: limit retries

    def run_modification_loop(self, instruction: str, doc_context: List[Any], model_config: Dict[str, Any], initial_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes an agentic modification loop:
        1. Generate Code (or use initial_code)
        2. Execute
        3. Catch Error -> Self-Correct (Reflect) -> Re-execute
        """
        history = []
        attempt = 1
        
        reply = "I have drafted the changes based on your instruction."
        code = None

        # Use initial code if provided for the first attempt
        if initial_code:
             code = initial_code
             logger.info("Agentic Loop: Using initial code draft.")
        else:
             # Initial prompted generation
             # generate_code returns a string (the code) or error message starting with # Error
             code_or_error = self.llm.generate_code(instruction, doc_context, model_config=model_config)
             
             if not code_or_error or code_or_error.startswith("# Error"):
                 return {"success": False, "reply": "Failed to generate valid code.", "error": code_or_error}
             code = code_or_error

        while attempt <= self.max_retries + 1:
            logger.info(f"Agentic Loop: Attempt {attempt}")
            
            # Execute
            success, error_msg = self.doc_engine.execute_code(code)
            
            if success:
                logger.info("Agentic Loop: Execution Successful")
                # TODO: Optional Visual Verification (Did it actually change?)
                # For now, success execution is good enough for speed.
                return {
                    "success": True,
                    "code": code,
                    "reply": reply,
                    "preview": self.doc_engine.get_preview_data(),
                    "html_preview": self.doc_engine.get_html_preview()
                }
            
            # Failure -> Reflect and Fix
            logger.warning(f"Agentic Loop: Execution Failed: {error_msg}")
            attempt += 1
            
            if attempt > self.max_retries + 1:
                break
                
            # Self-Correction Step
            fix_instruction = f"""
            The previous code failed with the following error:
            {error_msg}
            
            Please fix the Python code to strictly follow the instruction: {instruction}
            """
            
            # Re-call LLM with error context
            # We treat this as a "fix" task
            new_code_or_error = self.llm.generate_code(fix_instruction, doc_context, model_config=model_config)
            
            if new_code_or_error and not new_code_or_error.startswith("# Error"):
                code = new_code_or_error
                reply = "I encountered an error but I have attempted to fix it."
            else:
                # If LLM refuses to give code or errors again, we abort
                break
                
        return {"success": False, "reply": "Failed to execute changes after multiple attempts.", "error": error_msg}
