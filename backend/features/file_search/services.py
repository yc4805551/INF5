"""
文件搜索服务
结合 Everything 快速检索和 AI 智能排序
"""
import logging
from typing import List, Dict, Optional
from core.everything_client import EverythingClient

logger = logging.getLogger(__name__)


class FileSearchService:
    """文件搜索服务"""
    
    def __init__(self):
        """初始化服务"""
        self.everything_client = EverythingClient()
    
    def smart_search(
        self,
        query: str,
        file_types: Optional[List[str]] = None,
        date_range: Optional[str] = None,
        max_results: int = 20,
        enable_ai_ranking: bool = True
    ) -> Dict:
        """
        智能文件搜索
        
        Args:
            query: 搜索查询（支持自然语言或关键词）
            file_types: 文件类型过滤，如 ['.docx', '.xlsx']
            date_range: 时间范围，如 'today', 'lastweek', 'lastmonth'
            max_results: 最多返回结果数
            enable_ai_ranking: 是否启用 AI 排序
            
        Returns:
            {
                'success': bool,
                'query': str,
                'total': int,
                'results': [
                    {
                        'name': str,
                        'path': str,
                        'size': int,
                        'date_modified': str,
                        'ai_score': float,  # 如果启用 AI 排序
                        'ai_reason': str,   # AI 推荐理由
                    }
                ],
                'error': str  # 如果失败
            }
        """
        try:
            logger.info(f"Smart search: query='{query}', types={file_types}, date_range={date_range}")
            
            # Step 1: 使用 Everything 快速检索
            results = self.everything_client.search_with_filters(
                keywords=query,
                file_types=file_types,
                date_range=date_range,
                max_results=max_results * 2  # 获取更多候选，供 AI 筛选
            )
            
            logger.info(f"Everything returned {len(results)} results")
            
            # Step 2: AI 智能排序（如果启用）
            if enable_ai_ranking and results:
                results = self._ai_rank_files(query, results, max_results)
            else:
                # 只取前 N 个结果
                results = results[:max_results]
            
            # Step 3: 返回结果
            return {
                'success': True,
                'query': query,
                'total': len(results),
                'results': results,
                'file_types': file_types,
                'date_range': date_range
            }
        
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {
                'success': False,
                'query': query,
                'total': 0,
                'results': [],
                'error': str(e)
            }
    
    def _ai_rank_files(self, query: str, files: List[Dict], max_results: int) -> List[Dict]:
        """
        使用 AI 对文件进行智能排序
        
        Args:
            query: 用户查询
            files: 候选文件列表
            max_results: 返回前 N 个结果
            
        Returns:
            排序后的文件列表（包含 ai_score 和 ai_reason 字段）
        """
        try:
            from features.file_search.ai_ranker import rank_files
            
            # 调用 AI 排序模块
            ranked_files = rank_files(query, files, max_results)
            return ranked_files
        
        except Exception as e:
            logger.warning(f"AI ranking failed, fallback to original order: {e}")
            # AI 排序失败，返回原始结果
            return files[:max_results]
    
    def quick_search(self, query: str, max_results: int = 10) -> Dict:
        """
        快速搜索（不启用 AI 排序）
        
        Args:
            query: 搜索关键词
            max_results: 最多返回结果数
            
        Returns:
            搜索结果
        """
        return self.smart_search(
            query=query,
            max_results=max_results,
            enable_ai_ranking=False
        )
    
    def search_documents(self, query: str, max_results: int = 10) -> Dict:
        """
        搜索文档（.docx, .pdf, .md）
        
        Args:
            query: 搜索关键词
            max_results: 最多返回结果数
            
        Returns:
            搜索结果
        """
        return self.smart_search(
            query=query,
            file_types=['.docx', '.pdf', '.md', '.txt'],
            max_results=max_results
        )
    
    def search_spreadsheets(self, query: str, max_results: int = 10) -> Dict:
        """
        搜索表格（.xlsx, .xls, .csv）
        
        Args:
            query: 搜索关键词
            max_results: 最多返回结果数
            
        Returns:
            搜索结果
        """
        return self.smart_search(
            query=query,
            file_types=['.xlsx', '.xls', '.csv'],
            max_results=max_results
        )
