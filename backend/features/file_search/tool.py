"""
文件搜索 Agent 工具
用于在 Agent 对话中调用文件搜索功能
"""
import logging
from typing import Dict, Any, Optional, List
from features.file_search.services import FileSearchService

logger = logging.getLogger(__name__)

# 创建搜索服务实例
_search_service = FileSearchService()


# 工具定义（供 Agent 使用）
FILE_SEARCH_TOOL = {
    "name": "file_search",
    "description": """在本地文件系统中搜索文件。
    
    使用场景：
    - 用户询问："帮我找一下关于智慧城市的文档"
    - 用户询问："上周的预算表在哪里"
    - 用户询问："有没有关于AI的PPT"
    
    工具能力：
    - 快速搜索整个文件系统（基于 Everything 引擎）
    - 支持文件类型过滤（文档、表格等）
    - 支持时间范围过滤（今天、上周、上月）
    - AI 智能排序和推荐
    
    注意：
    - 只搜索文件名和路径，不读取文件内容
    - 主要用于快速定位文件位置
    """,
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词，支持中文和英文。例如：'智慧城市'、'预算'、'AI培训'"
            },
            "file_types": {
                "type": "array",
                "items": {"type": "string"},
                "description": "文件类型过滤（可选）。例如：['.docx', '.xlsx', '.pdf']。如果不指定，则搜索所有文件类型。",
                "default": None
            },
            "date_range": {
                "type": "string",
                "enum": ["today", "yesterday", "lastweek", "lastmonth", "lastyear"],
                "description": "时间范围过滤（可选）。可选值：today（今天）、yesterday（昨天）、lastweek（上周）、lastmonth（上月）、lastyear（去年）",
                "default": None
            },
            "max_results": {
                "type": "integer",
                "description": "最多返回结果数（可选），默认 10，最大 50",
                "default": 10,
                "minimum": 1,
                "maximum": 50
            }
        },
        "required": ["query"]
    }
}


def execute_file_search(
    query: str,
    file_types: Optional[List[str]] = None,
    date_range: Optional[str] = None,
    max_results: int = 10,
    **kwargs
) -> Dict[str, Any]:
    """
    执行文件搜索（供 Agent 调用）
    
    Args:
        query: 搜索关键词
        file_types: 文件类型过滤
        date_range: 时间范围
        max_results: 最多返回结果数
        
    Returns:
        搜索结果字典
    """
    try:
        logger.info(f"Agent file search: query='{query}', types={file_types}, date_range={date_range}")
        
        # 调用搜索服务
        result = _search_service.smart_search(
            query=query,
            file_types=file_types,
            date_range=date_range,
            max_results=max_results,
            enable_ai_ranking=True
        )
        
        # 如果搜索成功，格式化结果为 Agent 友好的格式
        if result['success']:
            files = result['results']
            
            if not files:
                return {
                    "status": "success",
                    "message": f"没有找到匹配 '{query}' 的文件。",
                    "total": 0,
                    "files": []
                }
            
            # 格式化文件列表
            formatted_files = []
            for i, file in enumerate(files[:10], 1):  # 最多显示前 10 个
                file_info = {
                    "index": i,
                    "name": file.get('name'),
                    "path": file.get('path'),
                    "size_kb": round(file.get('size', 0) / 1024, 2),
                    "is_recommended": file.get('is_recommended', False)
                }
                
                # 添加 AI 推荐信息
                if file.get('ai_score'):
                    file_info['ai_score'] = file.get('ai_score')
                    file_info['ai_reason'] = file.get('ai_reason', '')
                
                formatted_files.append(file_info)
            
            # 构造 Agent 响应消息
            message_lines = [
                f"找到 {result['total']} 个匹配 '{query}' 的文件：\n"
            ]
            
            for file in formatted_files:
                prefix = "⭐ " if file['is_recommended'] else "   "
                message_lines.append(
                    f"{prefix}{file['index']}. {file['name']}"
                )
                message_lines.append(f"    路径：{file['path']}")
                if file.get('ai_reason'):
                    message_lines.append(f"    推荐理由：{file['ai_reason']}")
                message_lines.append("")  # 空行
            
            # 如果有更多结果未显示
            if result['total'] > len(formatted_files):
                message_lines.append(
                    f"(还有 {result['total'] - len(formatted_files)} 个文件未显示)"
                )
            
            return {
                "status": "success",
                "message": "\n".join(message_lines),
                "total": result['total'],
                "files": formatted_files
            }
        else:
            # 搜索失败
            error_msg = result.get('error', '未知错误')
            return {
                "status": "error",
                "message": f"文件搜索失败：{error_msg}",
                "total": 0,
                "files": []
            }
    
    except Exception as e:
        logger.error(f"File search tool error: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"搜索出错：{str(e)}",
            "total": 0,
            "files": []
        }


# 导出工具
def get_file_search_tool():
    """返回文件搜索工具定义"""
    return {
        "definition": FILE_SEARCH_TOOL,
        "executor": execute_file_search
    }
