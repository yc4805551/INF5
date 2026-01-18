"""
文件搜索 Agent 工具
用于在 Agent 对话中调用文件搜索功能
"""
import logging
import json
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


# 工具定义（供 Agent 使用）
FILE_SEARCH_TOOL = {
    "name": "file_search",
    "description": """🔍 在本地文件系统中搜索文件。支持自然语言查询和多轮对话。
    
    使用场景：
    - 用户询问："帮我找一下关于智慧城市的文档"
    - 用户追问："最近一周修改的"（会自动细化之前的搜索）
    - 用户询问："有没有关于AI的PPT"
    
    工具能力：
    - 快速搜索整个文件系统（基于 Everything 引擎）
    - AI 自然语言理解和智能筛选
    - 支持多轮对话和渐进式筛选
    - 相关度评分和推荐理由
    - 智能推荐相关文件
    """,
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索查询，支持自然语言描述。例如：'帮我找最近关于吴军的课程PPT'，或追问：'最近一周的'"
            },
            "max_results": {
                "type": "integer",
                "description": "最多返回多少个结果，默认 10",
                "default": 10,
                "minimum": 1,
                "maximum": 20
            }
        },
        "required": ["query"]
    }
}


def execute(query: str, max_results: int = 10) -> str:
    """
    执行文件搜索（供 Agent 调用）
    
    Args:
        query: 搜索查询（支持自然语言）
        max_results: 最多返回多少个结果
        
    Returns:
        格式化的搜索结果（Markdown + JSON 元数据）
    """
    try:
        from features.file_search.search_agent import FileSearchAgent
        from features.file_search.services import FileSearchService
        
        logger.info(f"File search tool called: query='{query}', max_results={max_results}")
        
        # 初始化服务
        agent = FileSearchAgent()
        service = FileSearchService()
        
        # 执行智能搜索
        result = agent.smart_search(
            natural_language_query=query,
            everything_search_func=service.everything_client.search_with_filters,
            max_candidates=100,
            top_k=max_results
        )
        
        if not result['success']:
            return f"❌ 搜索失败：{result.get('error', '未知错误')}"
        
        files = result.get('results', [])
        ai_analysis = result.get('ai_analysis', '')
        
        if len(files) == 0:
            return f"🔍 未找到匹配的文件。\n\n搜索关键词：**{query}**\n\n💡 建议：\n- 尝试使用不同的关键词\n- 检查文件类型或时间范围"
        
        # 构建 JSON 元数据（供前端解析）
        metadata = {
            "files": files,
            "ai_analysis": ai_analysis,
            "total_candidates": result.get('total_candidates', 0),
            "intent": result.get('intent', '')
        }
        
        # 构建 Markdown 输出
        output = f"📁 **{ai_analysis}**\n\n"
        
        # 嵌入 JSON 元数据（前端会解析这部分）
        output += f"<!-- FILE_SEARCH_RESULT -->\n{json.dumps(metadata, ensure_ascii=False)}\n<!-- /FILE_SEARCH_RESULT -->\n\n"
        
        # 添加文件列表（Markdown 格式）
        for i, file in enumerate(files, 1):
            name = file.get('name', '未知文件')
            path = file.get('path', '')
            score = file.get('score')
            reason = file.get('reason', '')
            size = file.get('size', 0)
            date = file.get('date_modified', '')
            
            # 格式化文件大小
            if size:
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
            else:
                size_str = "-"
            
            output += f"**{i}. {file['name']}**\n"
            
            if score is not None:
                output += f"   ⭐ 相关度：{score}/100"
            if size_str != "-":
                output += f" • {size_str}"
            if date:
                output += f" • {date}"
            output += "\n"
            
            if path:
                output += f"   📍 `{path}`\n"
            
            if reason:
                output += f"   💡 {reason}\n"
            
            output += "\n"
        
        logger.info(f"File search tool returned {len(files)} results")
        return output.strip()
        
    except Exception as e:
        import traceback
        logger.error(f"File search tool error: {e}\n{traceback.format_exc()}")
        return f"❌ 搜索出错：{str(e)}\n\n请稍后重试或联系管理员。"


# 导出工具
def get_file_search_tool():
    """返回文件搜索工具定义"""
    return {
        "definition": FILE_SEARCH_TOOL,
        "executor": execute
    }
