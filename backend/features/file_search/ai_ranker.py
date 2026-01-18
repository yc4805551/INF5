"""
AI 文件排序模块
使用 LLM 对文件进行智能排序和推荐
"""
import logging
from typing import List, Dict
import json

logger = logging.getLogger(__name__)


def rank_files(query: str, files: List[Dict], max_results: int = 10) -> List[Dict]:
    """
    使用 AI 对文件列表进行智能排序
    
    当前实现：基于规则的排序（作为 AI 的 fallback）
    未来可集成 LLM 进行更智能的排序
    
    排序策略：
    1. 文件名相关度（40%）
    2. 路径相关度（30%）
    3. 时间新鲜度（20%）
    4. 文件类型匹配（10%）
    
    Args:
        query: 用户查询
        files: 候选文件列表
        max_results: 返回前 N 个结果
        
    Returns:
        排序后的文件列表（包含 ai_score 和 ai_reason 字段）
    """
    try:
        # 为每个文件计算评分
        scored_files = []
        query_lower = query.lower()
        query_keywords = set(query_lower.split())
        
        for file in files:
            file_name = file.get('name', '').lower()
            file_path = file.get('path', '').lower()
            
            # 计算各维度得分
            name_score = _calculate_name_score(file_name, query_lower, query_keywords)
            path_score = _calculate_path_score(file_path, query_keywords)
            time_score = 0  # TODO: 基于修改时间计算
            type_score = 0  # TODO: 基于文件类型计算
            
            # 加权总分
            total_score = (
                name_score * 0.4 +
                path_score * 0.3 +
                time_score * 0.2 +
                type_score * 0.1
            )
            
            # 生成推荐理由
            reason = _generate_reason(file_name, file_path, query, name_score, path_score)
            
            # 添加评分信息到文件对象
            file_with_score = file.copy()
            file_with_score['ai_score'] = round(total_score, 2)
            file_with_score['ai_reason'] = reason
            file_with_score['is_recommended'] = total_score >= 70  # 分数 >= 70 标记为推荐
            
            scored_files.append(file_with_score)
        
        # 按分数降序排序
        scored_files.sort(key=lambda x: x['ai_score'], reverse=True)
        
        # 返回前 N 个结果
        return scored_files[:max_results]
    
    except Exception as e:
        logger.error(f"File ranking failed: {e}")
        # 失败时返回原始列表
        return files[:max_results]


def _calculate_name_score(file_name: str, query: str, query_keywords: set) -> float:
    """
    计算文件名相关度得分（0-100）
    
    策略：
    - 完全匹配：100 分
    - 包含完整查询：80 分
    - 包含所有关键词：60 分
    - 包含部分关键词：40 分
    - 其他：20 分
    """
    # 完全匹配
    if query in file_name:
        return 100.0
    
    # 检查关键词匹配
    matched_keywords = sum(1 for kw in query_keywords if kw in file_name)
    total_keywords = len(query_keywords)
    
    if total_keywords == 0:
        return 20.0
    
    match_ratio = matched_keywords / total_keywords
    
    if match_ratio == 1.0:
        return 80.0
    elif match_ratio >= 0.5:
        return 60.0
    elif match_ratio > 0:
        return 40.0
    else:
        return 20.0


def _calculate_path_score(file_path: str, query_keywords: set) -> float:
    """
    计算路径相关度得分（0-100）
    
    策略：
    - 路径中包含关键词越多，分数越高
    """
    if not query_keywords:
        return 50.0
    
    matched_keywords = sum(1 for kw in query_keywords if kw in file_path)
    match_ratio = matched_keywords / len(query_keywords)
    
    return match_ratio * 100


def _generate_reason(file_name: str, file_path: str, query: str, name_score: float, path_score: float) -> str:
    """
    生成推荐理由
    """
    reasons = []
    
    if name_score >= 80:
        reasons.append(f"文件名与 '{query}' 高度匹配")
    elif name_score >= 60:
        reasons.append(f"文件名包含搜索关键词")
    
    if path_score >= 60:
        reasons.append("路径相关性高")
    
    if not reasons:
        reasons.append("可能相关")
    
    return "；".join(reasons)


def rank_files_with_llm(query: str, files: List[Dict], max_results: int = 10) -> List[Dict]:
    """
    使用 LLM 进行智能排序（未来实现）
    
    可以调用 Gemini/GPT 等模型，让 AI 理解用户意图并推荐最相关的文件
    
    Args:
        query: 用户查询
        files: 候选文件列表
        max_results: 返回前 N 个结果
        
    Returns:
        AI 排序后的文件列表
    """
    # TODO: 集成 LLM API
    # 1. 构造 prompt，包含用户查询和候选文件列表
    # 2. 调用 LLM 获取排序结果和推荐理由
    # 3. 解析 LLM 返回的结果
    
    logger.info("LLM ranking not implemented yet, using rule-based ranking")
    return rank_files(query, files, max_results)
