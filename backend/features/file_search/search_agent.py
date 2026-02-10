"""
AI 文件搜索助手
使用大语言模型理解自然语言查询，生成多维搜索策略，并智能筛选结果
"""
import logging
import json
import os
from typing import List, Dict, Optional
from core.llm_helper import call_llm

logger = logging.getLogger(__name__)


class FileSearchAgent:
    """AI 文件搜索助手"""
    
    INTENT_UNDERSTANDING_PROMPT = """你是一个文件搜索专家。用户会用自然语言描述他们想找的文件。
你的任务：分析用户意图，生成 **5-8组** 不同的搜索关键词策略，以通过 "Everything" 搜索引擎最大限度地找到目标文件。目标是**极大地提高召回率**，哪怕找偏了也没关系。

### 为什么需要多组策略？
用户输入的词可能与文件名不完全匹配。你需要尝试：
1.  **精确拆分**：将长句拆分为核心词 (AND 关系，用空格分隔)。
2.  **暴力拆分**：如果核心词很长，尝试拆成单字或短词。
3.  **通配符(*)**：**非常重要**！Everything 支持 `*`。例如搜 "报告" -> `*报告*`。对于英文，搜 "plan" -> `*plan*`。
4.  **同义词/近义词**：例如 "大模型" -> "LLM", "GPT", "AI"。
5.  **拼音/缩写**：例如 "工作日报" -> "日报", "周报", "report"。
6.  **文件扩展名**：如果用户找 PPT，记得显式加上 .ppt .pptx。

### 关键规则：
1.  **关键词**：Everything 默认空格是 AND。如果要 OR，用 `|`。例如 `报告|总结`。
2.  **停用词**：去除 "帮我找", "文档", "资料" 等无意义词。
3.  **排序**：将最可能的策略放在前面，但也必须包含一些"宽泛"的策略以防漏网。

请返回 JSON 格式结果：
{
  "strategies": [
    {
      "keywords": ["关键词1", "关键词2"],
      "desc": "策略描述，如 '精确匹配'"
    },
    {
       "keywords": ["*核心词*"],
       "desc": "通配符模糊搜索"
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
    ):
        """
        完整的智能搜索流程 (Streaming Generator)
        Yields:
            dict: Event data { type: str, data: any }
        """
        try:
            # Step 1: 理解意图
            yield {"type": "status", "message": "正在理解您的意图...", "step": "intent"}
            
            intent_data = self.understand_query(natural_language_query)
            strategies = intent_data.get('strategies', [])
            file_types = intent_data.get('file_types', [])
            time_range = intent_data.get('time_range', '')
            
            yield {"type": "intent", "data": intent_data}

            # ---------------------------------------------------------
            # Refinement: Prioritize Original Query & Skip C Drive
            # ---------------------------------------------------------
            # 1. Insert "Original Query" as the absolute first strategy
            original_strategy = {
                'keywords': [natural_language_query],
                'desc': '原始关键词 (Original)'
            }
            strategies.insert(0, original_strategy)
            # ---------------------------------------------------------

            all_candidates = []
            seen_paths = set()
            
            # Step 2: 执行搜索策略
            yield {"type": "status", "message": "正在执行多策略并行搜索...", "step": "searching"}
            
            for strategy in strategies:
                keywords_list = strategy.get('keywords', [])
                keywords_str = ' '.join(keywords_list)
                
                if not keywords_str:
                    continue
                
                desc = strategy.get('desc')
                yield {"type": "log", "message": f"尝试策略: {desc} -> 搜索 '{keywords_str}'"}
                
                # 2. Append !C: to skip C drive content
                final_query = f"{keywords_str} !C:"

                # 执行搜索
                results = everything_search_func(
                    keywords=final_query,
                    file_types=file_types if file_types else None,
                    date_range=time_range if time_range else None,
                    max_results=2000 
                )
                
                # DEBUG: Log exact params
                yield {"type": "log", "message": f"DEBUG: Strategy='{desc}', Keywords='{final_query}', Count={len(results)}"}

                # 实时处理新发现的结果
                new_items = []
                # 3. Dynamic Scoring: First strategy gets higher base score
                is_primary = (strategies.index(strategy) == 0)
                base_score = 80 if is_primary else 60

                for res in results:
                    # Enrich: Construct full path and Check is_dir
                    # Everything returns 'path' (parent dir) and 'name' (filename)
                    full_path = os.path.join(res.get('path', ''), res.get('name', ''))
                    res['path'] = full_path # Update to full absolute path
                    res['is_dir'] = os.path.isdir(full_path)

                    # Use full_path for deduplication!
                    path = res.get('path')
                    if path and path not in seen_paths:
                        res['_strategy_desc'] = desc
                        res['score'] = base_score # Allow downstream AI to adjust, but start higher
                        res['reason'] = f"来源: {desc}"
                        all_candidates.append(res)
                        seen_paths.add(path)
                        new_items.append(res)
                
                if new_items:
                    # 分批 Streaming 回传候选结果，让前端立即展示
                    yield {"type": "result_chunk", "data": new_items, "strategy": desc}
                
                if len(all_candidates) >= max_candidates:
                    break
            
            if not all_candidates:
                 yield {"type": "analysis", "data": "未找到匹配文件，请尝试更换关键词。"}
                 return

            # Step 3: AI 智能筛选
            yield {"type": "status", "message": f"已找到 {len(all_candidates)} 个文件，正在进行 AI 智能筛选...", "step": "filtering"}
            
            filtered_results = self.intelligent_filter(
                query=natural_language_query,
                candidates=all_candidates,
                top_k=top_k
            )
            
            # Step 4: 返回最终精选结果
            yield {"type": "final_results", "data": filtered_results}
            
            # Step 5: 生成总结
            strategy_names = [s.get('desc') for s in strategies] 
            strategy_text = "、".join(strategy_names[:2])
            ai_analysis = f"已通过 {strategy_text} 等策略找到 {len(all_candidates)} 个文件，并在其中精选了最相关的 {len(filtered_results)} 个置顶。"
            
            yield {"type": "analysis", "data": ai_analysis}
            
        except Exception as e:
            logger.error(f"Smart search failed: {e}", exc_info=True)
            yield {"type": "error", "message": str(e)}
