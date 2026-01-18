"""
Everything HTTP API 客户端
用于通过 HTTP 接口调用 Everything 文件搜索引擎
"""
import os
import logging
import requests
from typing import List, Dict, Optional
from urllib.parse import quote
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class EverythingClient:
    """Everything HTTP API 客户端封装"""
    
    def __init__(self):
        """从环境变量初始化配置"""
        self.base_url = os.getenv("EVERYTHING_HTTP_URL", "http://localhost:292")
        self.username = os.getenv("EVERYTHING_USERNAME", "")
        self.password = os.getenv("EVERYTHING_PASSWORD", "")
        self.timeout = int(os.getenv("EVERYTHING_TIMEOUT", "5"))
        
        # 验证配置
        if not self.base_url:
            logger.warning("EVERYTHING_HTTP_URL not configured")
    
    def _get_auth(self):
        """返回认证信息（如果配置了用户名密码）"""
        if self.username and self.password:
            return (self.username, self.password)
        return None
    
    def search(self, query: str, max_results: int = 20) -> List[Dict]:
        """
        基础搜索
        
        Args:
            query: 搜索关键词（支持 Everything 语法）
            max_results: 最多返回结果数
            
        Returns:
            文件列表，每个文件包含 name, path, size, date_modified 等字段
        """
        try:
            # 构建请求 URL - 添加字段参数
            # path=1: 返回完整路径
            # size=1: 返回文件大小
            # dm=1: 返回修改日期
            search_url = f"{self.base_url}/?search={quote(query)}&json=1&count={max_results}&path=1&size=1&dm=1"
            
            logger.info(f"Searching Everything: {query}")
            
            # 发送请求
            response = requests.get(
                search_url,
                auth=self._get_auth(),
                timeout=self.timeout
            )
            
            response.raise_for_status()
            data = response.json()
            
            # 解析结果
            results = data.get('results', [])
            logger.info(f"Found {len(results)} results")
            
            return results
            
        except requests.exceptions.ConnectionError:
            logger.error("Failed to connect to Everything HTTP server. Is it running?")
            raise Exception("无法连接到 Everything 服务，请确保 Everything HTTP 服务已启动")
        
        except requests.exceptions.Timeout:
            logger.error("Everything HTTP request timed out")
            raise Exception("Everything 搜索超时")
        
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error("Everything HTTP authentication failed")
                raise Exception("Everything 认证失败，请检查用户名和密码")
            else:
                logger.error(f"Everything HTTP error: {e}")
                raise Exception(f"Everything HTTP 错误: {e}")
        
        except Exception as e:
            logger.error(f"Unexpected error during Everything search: {e}")
            raise
    
    def search_with_filters(
        self,
        keywords: str,
        file_types: Optional[List[str]] = None,
        date_range: Optional[str] = None,
        max_results: int = 20
    ) -> List[Dict]:
        """
        高级搜索（带过滤条件）
        
        Args:
            keywords: 搜索关键词
            file_types: 文件类型列表，如 ['.docx', '.xlsx']
            date_range: 时间范围，如 'today', 'lastweek', 'lastmonth'
            max_results: 最多返回结果数
            
        Returns:
            文件列表
        """
        # 构造 Everything 查询语法
        query_parts = [keywords]
        
        # 添加文件类型过滤
        if file_types:
            # 将 ['.docx', '.xlsx'] 转换为 '*.docx|*.xlsx'
            type_pattern = '|'.join([f'*{ext}' if ext.startswith('.') else f'*.{ext}' 
                                     for ext in file_types])
            query_parts.append(type_pattern)
        
        # 添加时间范围过滤
        if date_range:
            query_parts.append(f"dm:{date_range}")
        
        # 合并查询
        query = ' '.join(query_parts)
        
        logger.info(f"Advanced search query: {query}")
        return self.search(query, max_results)
    
    def _build_search_query(
        self,
        keywords: str,
        file_types: Optional[List[str]] = None,
        date_range: Optional[str] = None
    ) -> str:
        """
        构造 Everything 查询语法
        
        Everything 语法参考：
        - *.docx: 匹配所有 .docx 文件
        - dm:today: 今天修改的文件
        - dm:lastweek: 上周修改的文件
        - size:>1mb: 大于 1MB 的文件
        """
        query_parts = []
        
        # 关键词
        if keywords:
            query_parts.append(keywords)
        
        # 文件类型
        if file_types:
            type_query = ' OR '.join([f'ext:{ext.lstrip(".")}' for ext in file_types])
            query_parts.append(f'({type_query})')
        
        # 时间范围
        if date_range:
            query_parts.append(f'dm:{date_range}')
        
        return ' '.join(query_parts)
    
    def test_connection(self) -> bool:
        """
        测试连接是否正常
        
        Returns:
            True 如果连接成功，False 否则
        """
        try:
            # 执行一个简单的搜索测试
            self.search("test", max_results=1)
            logger.info("Everything connection test successful")
            return True
        except Exception as e:
            logger.error(f"Everything connection test failed: {e}")
            return False
