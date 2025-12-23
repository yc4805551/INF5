from core.docx_engine import DocxEngine
from core.llm_engine import LLMEngine

# Global instances (Singleton pattern as per original design)
current_engine = DocxEngine()
llm_engine = LLMEngine()
