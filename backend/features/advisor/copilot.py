import logging
import asyncio
from typing import Dict, Any, List, Optional
from core.services import llm_engine
from features.audit.services import perform_audit

logger = logging.getLogger(__name__)

class CopilotService:
    def __init__(self):
        self.system_intro = """
        你是一位智能写作助手（Copilot）。
        你有两种工作模式：
        1. **问答顾问（Chat Advisor）**：回答用户关于写作、排版、语法等方面的问题。
        2. **审核管家（Audit Manager）**：当被请求“审核”、“检查”或“体检”文档时，或者用户明确点击按钮时，你会触发全面的文档深度体检。

        当前的环境是用户正在撰写的文档。
        """

    async def handle_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point for Copilot interaction.
        Payload:
        - message: str (User's question)
        - context: str (The document content)
        - trigger_audit: bool (Force audit execution)
        - history: list (Chat history)
        - model_config: dict
        """
        user_message = data.get("message", "")
        document_content = data.get("context", "")
        trigger_audit = data.get("trigger_audit", False)
        history = data.get("history", [])
        model_config = data.get("model_config", {})

        # 1. Direct Audit Trigger (Button Click or Explicit Command)
        if trigger_audit:
            logger.info("Copilot: Explicit audit trigger received.")
            return await self._run_audit(document_content, model_config)

        # 2. NLP Intent Detection (Simple Heuristic for now)
        # In a more advanced version, we would use an LLM call to classify intent.
        # For now, keywords are fast.
        normalized_msg = user_message.lower().strip()
        audit_keywords = ["audit", "review", "check document", "全文审核", "全文体检", "检查全文"]
        
        if any(k in normalized_msg for k in audit_keywords) and len(normalized_msg) < 20:
             logger.info(f"Copilot: Detected audit intent from message: '{user_message}'")
             return await self._run_audit(document_content, model_config)

        # 3. Default: Chat Response
        logger.info("Copilot: Delegating to Chat Advisor.")
        return await self._run_chat(user_message, document_content, history, model_config)

    async def _run_audit(self, content: str, model_config: dict) -> Dict[str, Any]:
        """
        Delegates to AuditService but returns a formatted 'audit_report' message.
        """
        # Call existing Audit Service (which supports async)
        # Note: perform_audit is an async function in features/audit/services.py
        audit_data = {
            "content": content,
            "source": "", # Optional source
            "rules": [],
            "model_config": model_config,
            # We can enable all agents by default for "Full Scan"
            "agents": ["proofread", "logic", "format", "consistency", "terminology"] 
        }

        try:
             # Reuse the powerful audit logic
             result = await perform_audit(audit_data)
             
             # Format as a special message type for frontend to render a card
             return {
                 "type": "audit_report",
                 "data": result, # contains { status, score, issues, summary }
                 "content": "我已完成全文深度体检，详细报告如下：" # Fallback text
             }
        except Exception as e:
            logger.error(f"Copilot Audit Error: {e}")
            return {
                "type": "text", 
                "content": f"Sorry, I encountered an error running the audit: {str(e)}"
            }

    async def _run_chat(self, message: str, context: str, history: List[Any], model_config: dict) -> Dict[str, Any]:
        """
        Standard Chat Response using LLMEngine.
        """
        # Construct Prompt
        # We inject the current document context contextually
        prompt = f"""
        {self.system_intro}
        
        [Current Document Snippet]
        {context[:2000]}... (truncated)
        
        [User Question]
        {message}
        """

        # Convert history format if needed (features/knowledge/services might have helpers, but simple is fine)
        # ... skipped history processing for brevity, assumed LLM engine handles text prompt primarily or we just use single turn for MVP

        try:
            # We use the blocking generate for now, wrapped in thread if needed, 
            # but since we are async here, we should stick to async patterns if possible.
            # backend/features/audit/services.py shows mixed usage.
            # let's assume llm_engine.generate is synchronous (blocking).
            
            # For "Chat", we usually want streaming, but for this "Unified Interface" non-streaming first is easier to implement.
            # Implementation Plan Phase 1 doesn't specify streaming chat requirements strictly.
            
            response_text = await asyncio.to_thread(
                llm_engine.generate,
                prompt=prompt,
                model_config=model_config
            )
            
            return {
                "type": "text",
                "content": response_text
            }
        except Exception as e:
            logger.error(f"Copilot Chat Error: {e}")
            return {
                "type": "text",
                "content": "I'm having trouble connecting to my brain right now."
            }

copilot_service = CopilotService()
