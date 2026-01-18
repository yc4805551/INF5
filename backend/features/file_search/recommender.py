"""
智能文件推荐
基于文件关联、相似度、使用历史等推荐相关文件
"""
import logging
from typing import List, Dict
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class FileRecommender:
    """文件推荐器"""
    
    @staticmethod
    def get_related_files(
        target_file: Dict,
        all_files: List[Dict],
        max_recommendations: int = 5
    ) -> List[Dict]:
        """
        获取相关文件推荐
        
        基于：
        1. 同目录文件
        2. 文件名相似
        3. 相同作者/主题
        
        Args:
            target_file: 目标文件
            all_files: 所有候选文件
            max_recommendations: 最多推荐数
            
        Returns:
            推荐文件列表
        """
        try:
            target_path = Path(target_file.get('path', ''))
            target_name = target_file.get('name', '')
            target_dir = target_path.parent
            
            recommendations = []
            
            for file in all_files:
                if file.get('path') == target_file.get('path'):
                    continue  # 跳过自己
                
                file_path = Path(file.get('path', ''))
                score = 0
                reason = []
                
                # 1. 同目录文件 (+50分)
                if file_path.parent == target_dir:
                    score += 50
                    reason.append("同目录")
                
                # 2. 文件名包含相同关键词 (+30分)
                target_words = set(target_name.lower().split())
                file_words = set(file.get('name', '').lower().split())
                common_words = target_words & file_words - {'.', '_', '-'}
                if len(common_words) > 0:
                    score += 30 * len(common_words)
                    reason.append(f"相似关键词: {', '.join(list(common_words)[:2])}")
                
                # 3. 相同文件类型 (+10分)
                if file_path.suffix == target_path.suffix:
                    score += 10
                    reason.append("相同类型")
                
                if score > 0:
                    recommendations.append({
                        **file,
                        'recommendation_score': score,
                        'recommendation_reason': ' • '.join(reason)
                    })
            
            # 按评分排序
            recommendations.sort(key=lambda x: x['recommendation_score'], reverse=True)
            
            return recommendations[:max_recommendations]
            
        except Exception as e:
            logger.error(f"Failed to get related files: {e}")
            return []
    
    @staticmethod
    def group_files_by_topic(files: List[Dict]) -> Dict[str, List[Dict]]:
        """
        按主题智能分组
        
        基于文件路径和名称中的关键词
        
        Args:
            files: 文件列表
            
        Returns:
            分组字典 {主题: [文件列表]}
        """
        try:
            groups = {}
            
            for file in files:
                path = Path(file.get('path', ''))
                
                # 尝试从路径提取主题
                path_parts = path.parts
                if len(path_parts) >= 2:
                    # 使用倒数第二级目录作为主题
                    topic = path_parts[-2] if len(path_parts) > 2 else path_parts[-1]
                else:
                    topic = "其他"
                
                if topic not in groups:
                    groups[topic] = []
                
                groups[topic].append(file)
            
            # 过滤掉只有1个文件的组
            groups = {k: v for k, v in groups.items() if len(v) > 1}
            
            return groups
            
        except Exception as e:
            logger.error(f"Failed to group files: {e}")
            return {}
    
    @staticmethod
    def group_files_by_time(files: List[Dict]) -> Dict[str, List[Dict]]:
        """
        按时间分组
        
        Args:
            files: 文件列表
            
        Returns:
            分组字典 {时间段: [文件列表]}
        """
        try:
            groups = {
                "今天": [],
                "本周": [],
                "本月": [],
                "更早": []
            }
            
            now = datetime.now()
            today = now.date()
            week_ago = (now - timedelta(days=7)).date()
            month_ago = (now - timedelta(days=30)).date()
            
            for file in files:
                date_str = file.get('date_modified', '')
                if not date_str:
                    groups["更早"].append(file)
                    continue
                
                try:
                    # 尝试解析日期
                    file_date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
                    
                    if file_date == today:
                        groups["今天"].append(file)
                    elif file_date >= week_ago:
                        groups["本周"].append(file)
                    elif file_date >= month_ago:
                        groups["本月"].append(file)
                    else:
                        groups["更早"].append(file)
                except:
                    groups["更早"].append(file)
            
            # 移除空组
            groups = {k: v for k, v in groups.items() if len(v) > 0}
            
            return groups
            
        except Exception as e:
            logger.error(f"Failed to group by time: {e}")
            return {}
