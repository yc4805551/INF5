"""
文件搜索路由
提供 RESTful API 端点
"""
import logging
from flask import Blueprint, request, jsonify, send_file, Response, stream_with_context
import os
import json
import requests
from urllib.parse import unquote, quote
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


# --- Remote Access Tools (Proxy & Stream) ---

EVERYTHING_LOCAL_URL = "http://127.0.0.1:292"
# EVERYTHING_AUTH = ('admin', 'password') # Uncomment if auth is needed locally

@file_search_bp.route('/search-proxy', methods=['GET'])
def proxy_search_file():
    """
    Proxy search requests to local Everything service.
    Solves the "Remote Browser -> Localhost" issue.
    
    Query Params:
    - q: Search query
    - count: Max results (default 20)
    """
    keyword = request.args.get('q', '').strip()
    if not keyword:
        return jsonify({"error": "No keyword provided"}), 400

    try:
        # Backend proxies the request to localhost Everything
        # json=1 is Everything's API param
        params = {
            "search": keyword,
            "json": 1, 
            "count": request.args.get('count', 20)
        }
        
        # logger.info(f"Proxying search to Everything: {keyword}")
        
        response = requests.get(
            EVERYTHING_LOCAL_URL, 
            params=params,
            # auth=EVERYTHING_AUTH, 
            timeout=5
        )
        
        if response.status_code != 200:
            logger.error(f"Everything proxy error: Status {response.status_code}")
            return jsonify({"error": f"Everything service returned {response.status_code}"}), 502

        data = response.json()
        return jsonify(data)
        
    except requests.exceptions.ConnectionError:
        logger.error("Everything service connection failed")
        return jsonify({"error": "Everything service unreachable (is it running on port 292?)"}), 503
    except Exception as e:
        logger.error(f"Proxy Search Error: {e}")
        return jsonify({"error": str(e)}), 500


@file_search_bp.route('/preview', methods=['GET'])
def preview_file():
    """
    Stream file content to browser for remote preview/download.
    Supports Chinese filenames via URL encoding.
    
    Query Params:
    - path: Absolute file path (URL encoded)
    """
    raw_path = request.args.get('path', '')
    if not raw_path:
        return "Missing path", 400
        
    # Python 3: unquote handles %xx escapes and UTF-8
    file_path = unquote(raw_path)
    
    # 🛡️ Security Check
    # Allow only specific drives (D:/, E:/) to prevent system file access
    # You can customize this list
    normalized_path = os.path.normpath(file_path)
    drive, _ = os.path.splitdrive(normalized_path)
    
    allowed_drives = ['d:', 'e:', 'f:', 'g:'] # Lowercase
    if drive.lower() not in allowed_drives:
        # Check if it's a safe subdirectory in C: (optional)
        # For now, strict block on C: root or system folders
        if drive.lower() == 'c:' and not ('users' in normalized_path.lower() or 'temp' in normalized_path.lower()):
             # logger.warning(f"Blocked access to safe path: {file_path}")
             return "Access Denied: Only D/E/F/G drives are allowed for remote preview.", 403
        
        # Fallback for other non-allowed drives
        return f"Access Denied: Drive {drive} is not allowed.", 403

    # Check if force download is requested
    force_download = request.args.get('download', '0') == '1'

    # Case 1: Directory Download (Zip it)
    if os.path.isdir(file_path):
        if force_download:
            try:
                # Create a zip stream in memory
                import zipfile
                import io
                
                # Limit zip size/time if necessary (omitted for now)
                memory_file = io.BytesIO()
                with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                    # Walk the directory
                    dirname = os.path.basename(file_path)
                    for root, dirs, files in os.walk(file_path):
                        for file in files:
                            abs_path = os.path.join(root, file)
                            # Relative path inside zip
                            rel_path = os.path.relpath(abs_path, os.path.dirname(file_path))
                            try:
                                zf.write(abs_path, rel_path)
                            except Exception as e:
                                logger.warning(f"Skipped file in zip: {abs_path} ({e})")
                
                memory_file.seek(0)
                return send_file(
                    memory_file,
                    mimetype='application/zip',
                    as_attachment=True,
                    download_name=f"{os.path.basename(file_path)}.zip"
                )
            except Exception as e:
                logger.error(f"Zip Error: {e}")
                return f"Failed to zip folder: {str(e)}", 500
        else:
            return "Cannot preview a directory. Please use download button.", 400

    # Case 2: File Preview/Download
    if not os.path.exists(file_path):
         return "File not found", 404

    try:
        # as_attachment=False attempts inline preview (PDF, Images, Text)
        # as_attachment=True forces download
        return send_file(file_path, as_attachment=force_download)
    except Exception as e:
        logger.error(f"File Stream Error: {e}")
        return f"Error streaming file: {str(e)}", 500
