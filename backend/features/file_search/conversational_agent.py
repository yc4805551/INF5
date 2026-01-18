"""
对话式文件搜索 Agent
支持多轮对话、上下文理解、渐进式筛选
"""
import logging
from typing import List, Dict, Optional
from features.file_search.search_agent import FileSearchAgent

logger = logging.getLogger(__name__)


class ConversationalSearchAgent(FileSearchAgent):
    """对话式搜索 Agent - 支持多轮对话"""
    
    CONTEXTUAL_PROMPT = """你是一个文件搜索助手。用户正在进行多轮对话搜索文件。

对话历史：
{history}

当前用户输入："{current_input}"

你的任务：
1. 理解用户意图（是新搜索还是细化之前的搜索）
2. 如果是细化搜索，结合之前的条件
3. 提取搜索参数

返回 JSON：
{{
  "is_refinement": true/false,  // 是否是细化之前的搜索
  "keywords": ["关键词"],
  "file_types": [".docx"],
  "time_range": "lastweek",
  "intent": "意图描述",
  "refinement_reason": "细化原因（如果是细化）"
}}

示例 1 - 新搜索：
历史: []
输入: "帮我找课程PPT"
返回: {{
  "is_refinement": false,
  "keywords": ["课程"],
  "file_types": [".pptx", ".ppt"],
  "intent": "查找课程PPT文件"
}}

示例 2 - 细化搜索：
历史: ["用户: 帮我找课程PPT", "助手: 找到127个课程PPT"]
输入: "吴军老师的"
返回: {{
  "is_refinement": true,
  "keywords": ["课程", "吴军"],
  "file_types": [".pptx", ".ppt"],
  "intent": "查找吴军老师的课程PPT",
  "refinement_reason": "用户进一步指定了老师姓名"
}}

示例 3 - 细化时间：
历史: ["用户: 找吴军的PPT", "助手: 找到8个文件"]
输入: "最近修改的"
返回: {{
  "is_refinement": true,
  "keywords": ["吴军"],
  "file_types": [".pptx", ".ppt"],
  "time_range": "lastweek",
  "intent": "查找吴军最近修改的PPT",
  "refinement_reason": "用户添加了时间限制"
}}

返回 JSON。
"""
    
    def __init__(self, model_provider: str = "gemini"):
        super().__init__(model_provider)
        self.conversation_history: List[Dict] = []
        self.last_search_params: Optional[Dict] = None
    
    def understand_contextual_query(
        self,
        user_input: str,
        history: List[Dict] = None
    ) -> Dict:
        """
        理解上下文查询（支持多轮对话）
        
        Args:
            user_input: 用户当前输入
            history: 对话历史
            
        Returns:
            搜索参数（可能结合了历史上下文）
        """
        try:
            from core.llm_helper import call_llm
            
            # 准备历史记录文本
            history_text = ""
            if history:
                for turn in history[-3:]:  # 只看最近3轮
                    history_text += f"{turn.get('role', 'user')}: {turn.get('text', '')}\n"
            
            # 调用 LLM 理解上下文
            prompt = self.CONTEXTUAL_PROMPT.format(
                history=history_text or "无",
                current_input=user_input
            )
            
            response = call_llm(
                provider=self.model_provider,
                system_prompt="你是搜索助手",
                user_prompt=prompt,
                temperature=0.3,
                json_mode=True
            )
            
            intent_data = self._parse_json_response(response)
            
            # 如果是细化搜索且有之前的参数，合并参数
            if intent_data.get('is_refinement') and self.last_search_params:
                # 合并关键词
                old_keywords = self.last_search_params.get('keywords', [])
                new_keywords = intent_data.get('keywords', [])
                intent_data['keywords'] = list(set(old_keywords + new_keywords))
                
                # 保留之前的文件类型（除非新指定了）
                if not intent_data.get('file_types'):
                    intent_data['file_types'] = self.last_search_params.get('file_types', [])
                
                logger.info(f"Refined search: {intent_data}")
            
            # 保存本次参数
            self.last_search_params = intent_data
            
            return intent_data
            
        except Exception as e:
            logger.error(f"Failed to understand contextual query: {e}")
            # 降级：返回原始查询
            return {
                'is_refinement': False,
                'keywords': [user_input],
                'file_types': [],
                'time_range': '',
                'intent': '关键词搜索'
            }
    
    def conversational_search(
        self,
        user_input: str,
        everything_search_func,
        history: List[Dict] = None,
        max_candidates: int = 100,
        top_k: int = 10
    ) -> Dict:
        """
        对话式搜索（支持多轮对话）
        
        Args:
            user_input: 用户输入
            everything_search_func: Everything 搜索函数
            history: 对话历史
            max_candidates: 最多候选数
            top_k: 返回结果数
            
        Returns:
            搜索结果
        """
        try:
            # 理解上下文意图
            intent = self.understand_contextual_query(user_input, history)
            
            # 执行搜索
            keywords = ' '.join(intent.get('keywords', []))
            file_types = intent.get('file_types', [])
            time_range = intent.get('time_range', '')
            
            candidates = everything_search_func(
                keywords=keywords,
                file_types=file_types if file_types else None,
                date_range=time_range if time_range else None,
                max_results=max_candidates
            )
            
            logger.info(f"Conversational search: {len(candidates)} candidates")
            
            # AI 智能筛选
            filtered_results = self.intelligent_filter(
                query=user_input,
                candidates=candidates,
                top_k=top_k
            )
            
            # 生成分析说明
            if intent.get('is_refinement'):
                ai_analysis = f"📍 细化搜索：{intent.get('refinement_reason', '')}，找到 {len(filtered_results)} 个文件"
            else:
                ai_analysis = f"🔍 {intent.get('intent', '搜索')}，找到 {len(filtered_results)} 个文件"
            
            return {
                'success': True,
                'query': user_input,
                'intent': intent.get('intent', ''),
                'is_refinement': intent.get('is_refinement', False),
                'total_candidates': len(candidates),
                'results': filtered_results,
                'ai_analysis': ai_analysis
            }
            
        except Exception as e:
            logger.error(f"Conversational search failed: {e}")
            return {
                'success': False,
                'query': user_input,
                'error': str(e),
                'results': []
            }
