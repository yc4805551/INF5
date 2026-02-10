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
            
            # Enrich results with is_dir flag (Check on final results to save IO)
            import os
            for res in results:
                # Construct full path to check file type
                full_path = os.path.join(res.get('path', ''), res.get('name', ''))
                is_directory = os.path.isdir(full_path)
                res['is_dir'] = is_directory
                # Minimal log for first few results to debug
                if results.index(res) < 5:
                     logger.info(f"Check: {full_path} -> is_dir={is_directory}")

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

    def open_file_location(self, path: str) -> Dict:
        """
        打开文件所在位置并选中文件
        
        Args:
            path: 文件完整路径
            
        Returns:
            Success status
        """
        try:
            import subprocess
            import os
            
            if not path:
                return {'success': False, 'error': 'Path is empty'}
                
            # 规范化路径
            norm_path = os.path.normpath(path)
            
            if not os.path.exists(norm_path):
                return {'success': False, 'error': 'File does not exist'}
            
            # 使用 explorer /select, <path> 打开并选中
            cmd = f'explorer /select,"{norm_path}"'
            subprocess.Popen(cmd, shell=True)
            
            logger.info(f"Opened file location: {norm_path}")
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Failed to open file location: {e}")
            return {'success': False, 'error': str(e)}

    def copy_to_clipboard(self, text: str) -> Dict:
        """
        复制文本到服务器端剪贴板 (Windows)
        
        Args:
            text: 要复制的文本
            
        Returns:
            Success status
        """
        try:
            import subprocess
            
            if not text:
                return {'success': False, 'error': 'Text is empty'}
                
            # 使用 clip 命令将文本写入剪贴板
            # echo text | clip (但在 Python 中用 subprocess.run 输入更安全)
            process = subprocess.run(
                ['clip'],
                input=text.strip(),
                text=True,  # 使用文本模式
                encoding='gbk', # Windows 剪贴板通常接受本地编码，但也尝试自适应
                shell=True  # Windows 下 clip 是 cmd 命令的一部分
            )
            
            if process.returncode == 0:
                logger.info(f"Copied to clipboard: {text[:50]}...")
                return {'success': True}
            else:
                return {'success': False, 'error': 'Clip command failed'}
            
        except Exception as e:
            logger.error(f"Failed to copy to clipboard: {e}")
            # Fallback retry with utf-16 if gbk fails (rare but possible)
            try:
                import subprocess
                subprocess.run(['clip'], input=text.strip(), text=True, encoding='utf-16', shell=True)
                return {'success': True}
            except Exception as e2:
                return {'success': False, 'error': str(e)}
