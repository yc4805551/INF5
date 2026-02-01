"""
文件搜索路由
提供 RESTful API 端点
"""
import logging
from flask import Blueprint, request, jsonify, send_file
import os
import json
from features.file_search.services import FileSearchService
from features.file_search.search_agent import FileSearchAgent

logger = logging.getLogger(__name__)

# 创建 Blueprint
file_search_bp = Blueprint('file_search', __name__)

# 创建服务实例
search_service = FileSearchService()
search_agent = FileSearchAgent()


@file_search_bp.route('/smart', methods=['POST'])
def smart_search():
    """
    AI 智能搜索 - 支持自然语言查询 (Streaming)
    
    Response:
        NDJSON stream (application/x-ndjson)
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请求体不能为空'}), 400
        
        query = data.get('query', '').strip()
        if not query:
            return jsonify({'success': False, 'error': '查询不能为空'}), 400
        
        max_results = min(data.get('maxResults', 10), 1000)
        model_provider = data.get('modelProvider', 'gemini')
        max_candidates = min(data.get('maxCandidates', 2000), 10000)
        
        logger.info(f"AI Smart search (Stream): query='{query}'")
        
        def generate():
            agent = FileSearchAgent(model_provider=model_provider)
            try:
                # 调用生成器
                for event in agent.smart_search(
                    natural_language_query=query,
                    everything_search_func=search_service.everything_client.search_with_filters,
                    max_candidates=max_candidates,
                    top_k=max_results
                ):
                    # 将事件序列化为 JSON 行
                    yield json.dumps(event, ensure_ascii=False) + '\n'
            except Exception as e:
                logger.error(f"Stream error: {e}")
                yield json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False) + '\n'
        
        from flask import Response, stream_with_context
        return Response(stream_with_context(generate()), mimetype='application/x-ndjson')

    except Exception as e:
        logger.error(f"Smart search error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': f'智能搜索失败: {str(e)}'}), 500


@file_search_bp.route('/search', methods=['POST'])
def search_files():
    """
    搜索文件
    
    请求体：
    {
        "query": "智慧城市",       # 必填：搜索关键词
        "fileTypes": [".docx", ".xlsx"],  # 可选：文件类型过滤
        "dateRange": "lastweek",   # 可选：时间范围 (today, lastweek, lastmonth)
        "maxResults": 10,          # 可选：最多返回结果数（默认 10）
        "enableAiRanking": true    # 可选：是否启用 AI 排序（默认 true）
    }
    
    响应：
    {
        "success": true,
        "query": "智慧城市",
        "total": 5,
        "results": [
            {
                "name": "智慧城市方案.docx",
                "path": "D:\\Projects\\智慧城市方案.docx",
                "size": 102400,
                "date_modified": "2024-01-15 14:30:00",
                "ai_score": 95.5,
                "ai_reason": "文件名与搜索关键词高度匹配",
                "is_recommended": true
            }
        ]
    }
    """
    try:
        # 解析请求参数
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': '请求体不能为空'
            }), 400
        
        query = data.get('query', '').strip()
        if not query:
            return jsonify({
                'success': False,
                'error': '查询关键词不能为空'
            }), 400
        
        file_types = data.get('fileTypes')
        date_range = data.get('dateRange')
        max_results = data.get('maxResults', 10)
        enable_ai_ranking = data.get('enableAiRanking', True)
        
        # 验证参数
        if max_results > 100:
            max_results = 100  # 限制最大结果数
        
        # 执行搜索
        logger.info(f"File search request: query='{query}', types={file_types}")
        
        result = search_service.smart_search(
            query=query,
            file_types=file_types,
            date_range=date_range,
            max_results=max_results,
            enable_ai_ranking=enable_ai_ranking
        )
        
        # 返回结果
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
    
    except Exception as e:
        logger.error(f"File search error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'搜索失败: {str(e)}'
        }), 500


@file_search_bp.route('/quick-search', methods=['GET'])
def quick_search():
    """
    快速搜索（GET 方式，不启用 AI 排序）
    
    查询参数：
    - q: 搜索关键词
    - limit: 最多返回结果数（默认 10）
    
    示例：GET /api/file-search/quick-search?q=智慧城市&limit=5
    """
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({
                'success': False,
                'error': '查询关键词不能为空'
            }), 400
        
        max_results = int(request.args.get('limit', 10))
        if max_results > 100:
            max_results = 100
        
        result = search_service.quick_search(query, max_results)
        
        return jsonify(result), 200 if result['success'] else 500
    
    except Exception as e:
        logger.error(f"Quick search error: {e}")
        return jsonify({
            'success': False,
            'error': f'搜索失败: {str(e)}'
        }), 500


@file_search_bp.route('/search/documents', methods=['POST'])
def search_documents():
    """
    搜索文档（.docx, .pdf, .md, .txt）
    
    请求体：
    {
        "query": "智慧城市",
        "maxResults": 10
    }
    """
    try:
        data = request.get_json() or {}
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({
                'success': False,
                'error': '查询关键词不能为空'
            }), 400
        
        max_results = data.get('maxResults', 10)
        result = search_service.search_documents(query, max_results)
        
        return jsonify(result), 200 if result['success'] else 500
    
    except Exception as e:
        logger.error(f"Document search error: {e}")
        return jsonify({
            'success': False,
            'error': f'文档搜索失败: {str(e)}'
        }), 500


@file_search_bp.route('/search/spreadsheets', methods=['POST'])
def search_spreadsheets():
    """
    搜索表格（.xlsx, .xls, .csv）
    
    请求体：
    {
        "query": "预算",
        "maxResults": 10
    }
    """
    try:
        data = request.get_json() or {}
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({
                'success': False,
                'error': '查询关键词不能为空'
            }), 400
        
        max_results = data.get('maxResults', 10)
        result = search_service.search_spreadsheets(query, max_results)
        
        return jsonify(result), 200 if result['success'] else 500
    
    except Exception as e:
        logger.error(f"Spreadsheet search error: {e}")
        return jsonify({
            'success': False,
            'error': f'表格搜索失败: {str(e)}'
        }), 500


@file_search_bp.route('/open', methods=['POST'])
def open_file_location():
    """
    打开文件所在位置
    
    请求体：
    {
        "path": "C:\\path\\to\\file.txt"
    }
    """
    try:
        data = request.get_json() or {}
        path = data.get('path', '').strip()
        
        if not path:
            return jsonify({'success': False, 'error': 'Path is required'}), 400
            
        result = search_service.open_file_location(path)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404 if 'not exist' in result.get('error', '') else 500
            
    except Exception as e:
        logger.error(f"Open location error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@file_search_bp.route('/download', methods=['GET'])
def download_file():
    """
    下载文件
    
    查询参数：
    - path: 文件完整路径
    """
    try:
        path = request.args.get('path', '').strip()
        
        if not path:
            return jsonify({'success': False, 'error': 'Path is required'}), 400
            
        if not os.path.exists(path):
            return jsonify({'success': False, 'error': 'File not found'}), 404
            
        return send_file(path, as_attachment=True)
            
    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@file_search_bp.route('/copy', methods=['POST'])
def copy_text():
    """
    复制文本到剪贴板
    
    请求体：
    {
        "text": "要复制的内容"
    }
    """
    try:
        data = request.get_json() or {}
        text = data.get('text') or data.get('path', '')
        text = str(text).strip()
        
        if not text:
            return jsonify({'success': False, 'error': 'Text is required'}), 400
            
        result = search_service.copy_to_clipboard(text)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"Copy error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@file_search_bp.route('/health', methods=['GET'])
def health_check():
    """
    检查 Everything 服务状态
    
    响应：
    {
        "status": "ok",  # 或 "error"
        "everything_connected": true,
        "message": "Everything service is running"
    }
    """
    try:
        is_connected = search_service.everything_client.test_connection()
        
        if is_connected:
            return jsonify({
                'status': 'ok',
                'everything_connected': True,
                'message': 'Everything service is running'
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'everything_connected': False,
                'message': 'Everything service is not responding'
            }), 503
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'everything_connected': False,
            'message': f'Health check failed: {str(e)}'
        }), 503
