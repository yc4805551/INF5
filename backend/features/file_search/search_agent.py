"""
AI 文件搜索助手
使用大语言模型理解自然语言查询，智能筛选文件搜索结果
"""
import logging
import json
from typing import List, Dict, Optional
from core.llm_helper import call_llm

logger = logging.getLogger(__name__)


class FileSearchAgent:
    """AI 文件搜索助手"""
    
    INTENT_UNDERSTANDING_PROMPT = """你是一个文件搜索助手。用户会用自然语言描述他们想找的文件。
你的任务：理解用户意图，提取**最细粒度**的组合关键词，以最大化搜索召回率（Everything 搜索引擎使用 "词A 词B" 的 AND 逻辑）。

### 关键规则：
1.  **拆分复合词**：严禁将长名词作为一个关键词。必须拆分为独立的词根。
    *   ❌ 错误：["碳效体系研究"] -> 只能搜到文件名包含连续"碳效体系研究"的文件。
    *   ✅ 正确：["碳效", "体系", "研究"] -> 可以搜到 "碳效评价指标体系研究..."。
2.  **去除停用词**：不要包含无意义的词，如 "帮我找", "有关", "相关", "的", "材料", "资料", "文档", "文件"。
3.  **提取核心实体**：只保留最核心的、独一无二的特征词。

请分析用户查询并返回 JSON 格式结果：
{
  "keywords": ["关键词1", "关键词2"],  // 细粒度的关键词列表
  "file_types": [".docx", ".pptx"],    // 推断的文件类型（可选）
  "time_range": "lastweek",             // 时间范围（today/yesterday/lastweek/lastmonth，可选）
  "intent": "用户意图的简短描述"
}

### 示例：
用户: "帮我找碳效体系研究的有关材料"
返回: {
  "keywords": ["碳效", "体系", "研究"],
  "file_types": [],
  "time_range": "",
  "intent": "搜索碳效体系研究资料"
}

用户: "最近关于人工智能大模型的PPT"
返回: {
  "keywords": ["人工智能", "大模型"],
  "file_types": [".pptx", ".ppt"],
  "time_range": "lastweek",
  "intent": "查找近期AI大模型演示文稿"
}

用户: "北碚区的项目合同"
返回: {
  "keywords": ["北碚", "项目", "合同"],
  "file_types": [".docx", ".pdf"],
  "time_range": "",
  "intent": "查找北碚区项目合同"
}

请仅返回 JSON，不要包含其他解释。
"""
    
    INTELLIGENT_FILTER_PROMPT = """你是一个文件搜索助手。用户搜索了"{query}"，从 Everything 获得了 {total} 个结果。

请从这些文件中选出最相关的前 {top_k} 个，并为每个文件打分（0-100）和说明推荐理由。

文件列表：
{file_list}

请返回 JSON 格式：
[
  {{
    "name": "文件名",
    "path": "完整路径",
    "score": 95,
    "reason": "文件名高度匹配查询关键词"
  }},
  ...
]

评分标准：
- 文件名与关键词匹配度（40%）
- 路径相关性（30%）
- 时间新鲜度（20%）
- 文件类型匹配（10%）

请仅返回 JSON 数组，不要包含其他解释。
"""
    
    def __init__(self, model_provider: str = "openai"):
        """
        初始化 AI 搜索助手
        
        Args:
            model_provider: LLM 提供商（gemini/openai/deepseek等）
        """
        self.model_provider = model_provider
    
    def understand_query(self, natural_language_query: str) -> Dict:
        """
        理解自然语言查询
        
        Args:
            natural_language_query: 用户的自然语言输入
            
        Returns:
            {
                'keywords': List[str],
                'file_types': List[str],
                'time_range': str,
                'intent': str
            }
        """
        try:
            logger.info(f"Understanding query: {natural_language_query}")
            
            # 调用 LLM 理解意图
            response = call_llm(
                provider=self.model_provider,
                system_prompt=self.INTENT_UNDERSTANDING_PROMPT,
                user_prompt=f"用户查询: {natural_language_query}",
                temperature=0.3,  # 低温度以获得更确定的结果
                json_mode=True
            )
            
            # 解析 JSON 响应
            intent_data = self._parse_json_response(response)
            
            logger.info(f"Understood intent: {intent_data}")
            return intent_data
        
        except Exception as e:
            logger.error(f"Failed to understand query: {e}")
            # 降级策略：返回原始查询作为关键词
            return {
                'keywords': [natural_language_query],
                'file_types': [],
                'time_range': '',
                'intent': '关键词搜索'
            }
    
    def intelligent_filter(
        self,
        query: str,
        candidates: List[Dict],
        top_k: int = 10
    ) -> List[Dict]:
        """
        AI 智能筛选结果
        
        Args:
            query: 用户查询
            candidates: 候选文件列表
            top_k: 返回前 K 个结果
            
        Returns:
            筛选后的文件列表，每个文件包含 score 和 reason 字段
        """
        try:
            if not candidates:
                return []
            
            if len(candidates) <= top_k:
                # 如果候选数量本身就不多，直接返回
                return candidates
            
            logger.info(f"Filtering {len(candidates)} candidates to top {top_k}")
            
            # 准备文件列表（简化信息以减少 token）
            file_list = []
            for i, file in enumerate(candidates[:50]):  # 最多分析前50个
                file_list.append({
                    'index': i,
                    'name': file.get('name', ''),
                    'path': file.get('path', ''),
                    'size': file.get('size', 0),
                    'date_modified': file.get('date_modified', '')
                })
            
            # 调用 LLM 进行智能筛选
            prompt = self.INTELLIGENT_FILTER_PROMPT.format(
                query=query,
                total=len(candidates),
                top_k=top_k,
                file_list=json.dumps(file_list, ensure_ascii=False, indent=2)
            )
            
            response = call_llm(
                provider=self.model_provider,
                system_prompt="你是一个专业的文件搜索助手。",
                user_prompt=prompt,
                temperature=0.3,
                json_mode=True
            )
            
            # 解析结果
            filtered_results = self._parse_json_response(response)
            
            if isinstance(filtered_results, list) and len(filtered_results) > 0:
                logger.info(f"AI filtered to {len(filtered_results)} results")
                
                # 补充完整的文件信息（AI 可能只返回部分字段）
                complete_results = []
                for ai_file in filtered_results[:top_k]:
                    # 找到原始文件数据
                    original_file = None
                    for candidate in candidates:
                        if candidate.get('name') == ai_file.get('name') or candidate.get('path') == ai_file.get('path'):
                            original_file = candidate
                            break
                    
                    if original_file:
                        # 合并 AI 评分和原始文件数据
                        complete_file = {
                            **original_file,  # 原始数据（包含 size, date_modified 等）
                            'score': ai_file.get('score'),  # AI 评分
                            'reason': ai_file.get('reason')  # AI 推荐理由
                        }
                        complete_results.append(complete_file)
                    else:
                        # 如果找不到原始文件，至少返回 AI 的数据
                        complete_results.append(ai_file)
                
                return complete_results
            else:
                # AI 筛选失败或返回空，降级返回原始结果（添加默认评分）
                logger.warning(f"AI filter returned empty or invalid, falling back to original {len(candidates[:top_k])} results")
                fallback_results = []
                for i, file in enumerate(candidates[:top_k]):
                    fallback_results.append({
                        **file,
                        'score': max(100 - i * 5, 50),  # 简单评分：第一个100分，递减
                        'reason': '基于文件名匹配'
                    })
                return fallback_results
        
        except Exception as e:
            logger.error(f"Failed to filter results: {e}")
            # 降级策略：返回前 K 个原始结果（添加默认评分）
            logger.info(f"Exception occurred, returning original {len(candidates[:top_k])} results")
            fallback_results = []
            for i, file in enumerate(candidates[:top_k]):
                fallback_results.append({
                    **file,
                    'score': max(100 - i * 5, 50),
                    'reason': '搜索结果'
                })
            return fallback_results
            return candidates[:top_k]
    
    def _parse_json_response(self, response: str) -> Dict:
        """解析 JSON 响应"""
        try:
            # 移除可能的 markdown 代码块
            cleaned = response.strip()
            if cleaned.startswith('```'):
                # 提取代码块内容
                lines = cleaned.split('\n')
                cleaned = '\n'.join(lines[1:-1])
            
            return json.loads(cleaned)
        except Exception as e:
            logger.error(f"Failed to parse JSON: {e}, response: {response}")
            raise
    
    def smart_search(
        self,
        natural_language_query: str,
        everything_search_func,
        max_candidates: int = 100,
        top_k: int = 10
    ) -> Dict:
        """
        完整的智能搜索流程
        
        Args:
            natural_language_query: 自然语言查询
            everything_search_func: Everything 搜索函数
            max_candidates: 最多获取多少候选结果
            top_k: 返回前 K 个结果
            
        Returns:
            {
                'success': bool,
                'query': str,
                'intent': str,
                'total_candidates': int,
                'results': List[Dict],
                'ai_analysis': str
            }
        """
        try:
            # Step 1: 理解用户意图
            intent = self.understand_query(natural_language_query)
            
            # Step 2: 构造 Everything 查询
            keywords = ' '.join(intent.get('keywords', []))
            file_types = intent.get('file_types', [])
            time_range = intent.get('time_range', '')
            
            # Step 3: 使用 Everything 快速检索
            candidates = everything_search_func(
                keywords=keywords,
                file_types=file_types if file_types else None,
                date_range=time_range if time_range else None,
                max_results=max_candidates
            )
            
            logger.info(f"Everything returned {len(candidates)} candidates")
            
            # Step 4: AI 智能筛选
            filtered_results = self.intelligent_filter(
                query=natural_language_query,
                candidates=candidates,
                top_k=top_k
            )
            
            # Step 5: 生成 AI 分析说明
            if len(filtered_results) > 0:
                ai_analysis = f"根据\"{intent.get('intent', '查询')}\"找到 {len(filtered_results)} 个最相关文件"
            elif len(candidates) > 0:
                # AI 筛选失败，但 Everything 有结果
                ai_analysis = f"关键词搜索找到 {len(candidates)} 个文件（AI 分析不可用，显示全部结果）"
                filtered_results = candidates[:top_k]  # 确保返回 Everything 结果
            else:
                # Everything 也没找到
                ai_analysis = "未找到匹配的文件"
            
            return {
                'success': True,
                'query': natural_language_query,
                'intent': intent.get('intent', ''),
                'total_candidates': len(candidates),
                'results': filtered_results,
                'ai_analysis': ai_analysis
            }
        
        except Exception as e:
            logger.error(f"Smart search failed: {e}")
            return {
                'success': False,
                'query': natural_language_query,
                'error': str(e),
                'total_candidates': 0,
                'results': []
            }
