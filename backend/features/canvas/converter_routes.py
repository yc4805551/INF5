"""
Canvas Converter Routes
提供快速画布与DOCX互转的API端点
"""
from flask import Blueprint, request, jsonify, send_file
from features.canvas_converter import tiptap_to_docx, docx_to_tiptap
import logging
import io

logger = logging.getLogger(__name__)

canvas_converter_bp = Blueprint('canvas_converter', __name__, url_prefix='/api/canvas')

@canvas_converter_bp.route('/export-to-docx', methods=['POST'])
def export_to_docx():
    """
    将快速画布（Tiptap JSON）导出为DOCX
    
    Request Body:
    {
        "content": {...}  // Tiptap JSON content
    }
    
    Response: DOCX文件流
    """
    try:
        data = request.get_json()
        
        if not data or 'content' not in data:
            return jsonify({"error": "Missing 'content' field"}), 400
        
        tiptap_json = data['content']
        
        # 转换为DOCX
        docx_buffer = tiptap_to_docx(tiptap_json)
        
        # 返回文件
        return send_file(
            docx_buffer,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            as_attachment=True,
            download_name='export.docx'
        )
    
    except Exception as e:
        logger.error(f"Export to DOCX failed: {e}")
        return jsonify({"error": str(e)}), 500

@canvas_converter_bp.route('/import-from-docx', methods=['POST'])
def import_from_docx():
    """
    将DOCX导入为快速画布（Tiptap JSON）
    
    Request: multipart/form-data with 'file' field
    
    Response:
    {
        "content": {...}  // Tiptap JSON
    }
    """
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"error": "Empty filename"}), 400
        
        if not file.filename.lower().endswith('.docx'):
            return jsonify({"error": "Only DOCX files are supported"}), 400
        
        # 读取文件流
        file_stream = io.BytesIO(file.read())
        
        # 转换为Tiptap JSON
        tiptap_json = docx_to_tiptap(file_stream)
        
        return jsonify(tiptap_json)
    
    except Exception as e:
        logger.error(f"Import from DOCX failed: {e}")
        return jsonify({"error": str(e)}), 500
