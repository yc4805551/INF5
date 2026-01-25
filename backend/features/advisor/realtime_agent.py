import logging
import json
from typing import List, Dict, Any, Optional
from core.llm_engine import LLMEngine

# Logger setup
logger = logging.getLogger(__name__)

class RealtimeAgent:
    """
    Independent Realtime Agent for sentence-level auditing.
    Implements Andrew Ng's Agentic Patterns:
    1. Reflection: Evaluate drafts critically before returning.
    2. Tool Use: (Future extensible)
    3. Structured Output: JSON-enforced.
    """

    def __init__(self):
        self.llm = LLMEngine()

    def analyze_sentence(self, text: str, model_config: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Analyzes a single sentence or short text block for errors.
        Focus: typos, grammar, logic, collocations (Chinese).
        Enforces 'Whole Sentence' view.
        """
        if not text or len(text.strip()) < 2:
            return []

        logger.info(f"RealtimeAgent analyzing: {text[:50]}...")

        # 1. Draft & Reflection Prompt
        # We ask the model to first generate suggestions, then critique them, then finalize.
        # This one-shot prompt simulates the reflection loop for speed (REALTIME constraint < 3s).
        prompt = f"""
        你是一位严格的中文文案编辑（实时智能体）。
        你的任务是：找出文本中的【错别字】、【语病】、【逻辑错误】和【搭配不当】。

        输入文本："{text}"

        请严格遵循以下【思考过程】（Thought Process，不要输出思考内容，只输出最终 JSON）：
        1. **整句分析 (Analyze)**：通读整句，理解语义 context。
        2. **初稿生成 (Draft)**：快速标记所有可能的错误点。
        3. **深度反思 (Reflect)**：
           - 这个“错误”真的是错误吗？还是特殊用法？
           - “原文”是否能在输入文本中精确找到？
           - “建议”是否真的比原文更好？
        4. **过滤筛选 (Filter)**：剔除吹毛求疵的风格建议，只保留确定的硬伤或重大改进。

        输出格式：JSON 对象列表
        [
            {{
                "id": "unique_id",
                "original": "输入中完全匹配的原文片段",
                "suggestion": "修改后的文本",
                "type": "proofread" (硬伤) | "polish" (润色),
                "reason": "简要说明理由"
            }}
        ]

        约束条件：
        - 如果没有明确错误，返回空列表 []。
        - "original" 必须存在于“输入文本”中。
        - "suggestion" 必须与 "original" 不同。
        """

        try:
            # Using generate_json for structured output
            response = self.llm.generate(prompt, model_config=model_config)
            
            # Simple parsing if response is raw text, but LLMEngine usually returns string
            # We need to extract JSON from it. 
            # Assuming LLMEngine.generate returns a string. We typically use a helper to parse JSON.
            # Let's try to parse it.
            
            suggestions_data = self._parse_json_response(response)
            return suggestions_data

        except Exception as e:
            logger.error(f"RealtimeAgent error: {e}")
            return []

    def _parse_json_response(self, response_text: str) -> List[Dict[str, Any]]:
        """Helper to safely parse JSON from LLM response"""
        try:
            # Clean up markdown code blocks if present
            cleaned = response_text.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned)
            if isinstance(data, list):
                # Enrich with IDs if missing (though prompt asks for it)
                for idx, item in enumerate(data):
                    if "id" not in item:
                        item["id"] = f"rt-{idx}"
                    # Default type
                    if "type" not in item:
                        item["type"] = "proofread"
                return data
            return []
        except json.JSONDecodeError:
            logger.warning(f"RealtimeAgent failed to parse JSON: {response_text[:100]}")
            return []

# Singleton instance
realtime_agent = RealtimeAgent()
