"""
AI 文件搜索助手
使用大语言模型理解自然语言查询，生成多维搜索策略，并智能筛选结果
"""
import logging
import json
from typing import List, Dict, Optional
from core.llm_helper import call_llm

logger = logging.getLogger(__name__)


class FileSearchAgent:
    """AI 文件搜索助手"""
    
    INTENT_UNDERSTANDING_PROMPT = """你是一个文件搜索专家。用户会用自然语言描述他们想找的文件。
你的任务：分析用户意图，生成 **3-5组** 不同的搜索关键词策略，以通过 "Everything" 搜索引擎最大限度地找到目标文件。

### 为什么需要多组策略？
用户输入的词可能与文件名不完全匹配。你需要尝试：
1.  **精确拆分**：将长句拆分为核心词 (AND 关系)。
2.  **同义词/近义词**：例如用户搜 "大模型"，你要试 "LLM"、"Transformer"、"人工智能"。
3.  **关联词**：例如用户搜 "合同"，你要试 "协议"、"签约"。
4.  **宽泛匹配**：减少关键词数量，提高召回率。

### 关键规则：
1.  **关键词**：Everything 默认是 AND 关系。
2.  **停用词**：去除 "帮我找", "文档", "资料" 等无意义词。
3.  **排序**：将最可能的策略放在前面。

请返回 JSON 格式结果：
{
  "strategies": [
    {
      "keywords": ["关键词1", "关键词2"],
      "desc": "策略描述，如 '精确匹配'"
    },
    {
      "keywords": ["同义词1", "同义词2"],
      "desc": "如同义词 '大模型' -> 'LLM'"
    }
  ],
  "file_types": [".docx", ".pptx"],    // 推断的文件类型（可选）
  "time_range": "lastweek",             // 时间范围（today/yesterday/lastweek/lastmonth，可选）
  "intent": "用户意图的简短描述"
}

### 示例：
用户: "帮我找碳效体系研究的有关材料"
返回:
{
  "strategies": [
    {"keywords": ["碳效", "体系", "研究"], "desc": "核心词精确匹配"},
    {"keywords": ["碳", "效率", "评价"], "desc": "相关概念扩展"},
    {"keywords": ["低碳", "体系"], "desc": "宽泛匹配"}
  ],
  "file_types": [],
  "time_range": "",
  "intent": "搜索碳效体系研究资料"
}

用户: "最近关于人工智能大模型的PPT"
返回:
{
  "strategies": [
    {"keywords": ["人工智能", "大模型"], "desc": "精确匹配"},
    {"keywords": ["AI", "Large Model"], "desc": "英文术语"},
    {"keywords": ["深度学习", "神经网络"], "desc": "相关技术词"}
  ],
  "file_types": [".pptx", ".ppt"],
  "time_range": "lastweek",
  "intent": "查找近期AI大模型演示文稿"
}

请仅返回 JSON，不要包含其他解释。
"""
    
    INTELLIGENT_FILTER_PROMPT = """你是一个文件搜索助手。用户搜索了"{query}"。
为了找到该文件，我们尝试了多种搜索策略，共找到了 {total} 个候选文件（已去重）。

请从这些文件中选出最相关的前 {top_k} 个，并为每个文件打分（0-100）和说明推荐理由。

文件列表：
{file_list}

请返回 JSON 格式：
[
  {{
    "name": "文件名",
    "path": "完整路径",
    "score": 95,
    "reason": "文件名包含'大模型'且时间较新"
  }},
  ...
]

评分标准：
- **语义匹配** (50%)：文件名/路径是否真正符合用户意图（不仅是关键词匹配）。
- **时间新鲜度** (20%)：近期文件通常更有价值。
- **文件重要性** (15%)：正式文档（如.docx）通常比临时文件（.chk）重要。
- **路径合理性** (15%)：位于“桌面”或“文档”目录的通常比“AppData”里的重要。

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
        理解自然语言查询，生成搜索策略
        """
        try:
            logger.info(f"Understanding query: {natural_language_query}")
            
            response = call_llm(
                provider=self.model_provider,
                system_prompt=self.INTENT_UNDERSTANDING_PROMPT,
                user_prompt=f"用户查询: {natural_language_query}",
                temperature=0.3,
                json_mode=True
            )
            
            intent_data = self._parse_json_response(response)
            logger.info(f"Generated {len(intent_data.get('strategies', []))} search strategies")
            return intent_data
        
        except Exception as e:
            logger.error(f"Failed to understand query: {e}")
            # 降级：仅生成一个基础策略
            return {
                'strategies': [{'keywords': [natural_language_query], 'desc': '原始查询'}],
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
        """
        try:
            if not candidates:
                return []
            
            if len(candidates) <= top_k:
                return candidates
            
            logger.info(f"Filtering {len(candidates)} candidates to top {top_k}")
            
            # 准备文件列表（简化信息）
            file_list = []
            for i, file in enumerate(candidates[:60]):  # 增加候选分析数量
                file_list.append({
                    'index': i,
                    'name': file.get('name', ''),
                    'path': file.get('path', ''),
                    'size': file.get('size', 0),
                    'date_modified': file.get('date_modified', '')
                })
            
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
            
            filtered_results = self._parse_json_response(response)
            
            if isinstance(filtered_results, list) and len(filtered_results) > 0:
                # 补充完整信息
                complete_results = []
                for ai_file in filtered_results[:top_k]:
                    original_file = None
                    for candidate in candidates:
                        # 尝试通过路径严格匹配，或者名称匹配
                        if candidate.get('path') == ai_file.get('path') or candidate.get('name') == ai_file.get('name'):
                            original_file = candidate
                            break
                    
                    if original_file:
                        complete_file = {
                            **original_file,
                            'score': ai_file.get('score', 0),
                            'reason': ai_file.get('reason', '')
                        }
                        complete_results.append(complete_file)
                    else:
                        complete_results.append(ai_file)
                
                return complete_results
            else:
                return self._fallback_ranking(candidates, top_k)
        
        except Exception as e:
            logger.error(f"Failed to filter results: {e}")
            return self._fallback_ranking(candidates, top_k)

    def _fallback_ranking(self, candidates, top_k):
        """简单的降级排序"""
        fallback_results = []
        for i, file in enumerate(candidates[:top_k]):
            fallback_results.append({
                **file,
                'score': max(100 - i * 5, 50),
                'reason': '基于文件名匹配 (AI未介入)'
            })
        return fallback_results
    
    def _parse_json_response(self, response: str) -> Dict:
        """解析 JSON"""
        try:
            cleaned = response.strip()
            if cleaned.startswith('```'):
                lines = cleaned.split('\\n')
                cleaned = '\\n'.join(lines[1:-1])
            return json.loads(cleaned)
        except Exception as e:
            logger.error(f"Failed to parse JSON: {e}")
            raise
    
    def smart_search(
        self,
        natural_language_query: str,
        everything_search_func,
        max_candidates: int = 2000,
        top_k: int = 10
    ) -> Dict:
        """
        完整的智能搜索流程 (Multi-Strategy)
        """
        try:
            # Step 1: 理解意图 & 生成多策略
            intent_data = self.understand_query(natural_language_query)
            strategies = intent_data.get('strategies', [])
            file_types = intent_data.get('file_types', [])
            time_range = intent_data.get('time_range', '')
            
            all_candidates = []
            seen_paths = set()
            used_strategies = []

            # Step 2: 并行/迭代执行所有策略
            logger.info(f"Executing {len(strategies)} search strategies...")
            
            for strategy in strategies:
                keywords_list = strategy.get('keywords', [])
                keywords_str = ' '.join(keywords_list)
                
                if not keywords_str:
                    continue
                    
                logger.info(f"Strategy: {strategy.get('desc')} -> '{keywords_str}'")
                
                results = everything_search_func(
                    keywords=keywords_str,
                    file_types=file_types if file_types else None,
                    date_range=time_range if time_range else None,
                    max_results=1000  # 每个策略限制结果数，防止爆炸
                )
                
                # 收集结果并去重
                added_count = 0
                for res in results:
                    path = res.get('path')
                    if path and path not in seen_paths:
                        res['_strategy_desc'] = strategy.get('desc') # 标记来源
                        all_candidates.append(res)
                        seen_paths.add(path)
                        added_count += 1
                
                if added_count > 0:
                    used_strategies.append(f"{strategy.get('desc')} ('{keywords_str}')")
                
                if len(all_candidates) >= max_candidates:
                    break
            
            logger.info(f"Total unique candidates found: {len(all_candidates)}")
            
            # Step 3: AI 智能筛选 (只筛选前 K 个，但保留其余结果)
            filtered_results = self.intelligent_filter(
                query=natural_language_query,
                candidates=all_candidates,
                top_k=top_k
            )
            
            # Step 4: 合并结果 (AI 排序 + 剩余结果)
            ranked_paths = {res.get('path') for res in filtered_results}
            final_results = list(filtered_results)
            
            for candidate in all_candidates:
                if candidate.get('path') not in ranked_paths:
                    candidate['score'] = 0
                    candidate['reason'] = '关键词匹配'
                    final_results.append(candidate)

            # Step 5: 生成 AI 分析说明
            if len(filtered_results) > 0:
                strategy_text = "、".join(used_strategies[:2])
                ai_analysis = f"已通过 {strategy_text} 等策略找到 {len(all_candidates)} 个文件，并为您精选了最相关的 {len(filtered_results)} 个置顶。"
            else:
                ai_analysis = "尝试了多种关键词组合，但未找到匹配文件。"
            
            return {
                'success': True,
                'query': natural_language_query,
                'intent': intent_data.get('intent', ''),
                'strategies_used': used_strategies,
                'total_candidates': len(all_candidates),
                'results': final_results,
                'ai_analysis': ai_analysis
            }
        
        except Exception as e:
            logger.error(f"Smart search failed: {e}", exc_info=True)
            return {
                'success': False,
                'query': natural_language_query,
                'error': str(e),
                'total_candidates': 0,
                'results': []
            }
