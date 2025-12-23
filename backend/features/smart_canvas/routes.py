from flask import Blueprint, request, jsonify, current_app
import logging
import os
from core.services import current_engine

smart_canvas_bp = Blueprint('smart_canvas', __name__)

@smart_canvas_bp.route('/upload', methods=['POST'])
def smart_canvas_upload():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        # Save uploaded file temporarily
        temp_path = os.path.join(current_app.root_path, 'temp_upload.docx')
        file.save(temp_path)
        
        # Image output directory
        images_dir = os.path.join(current_app.root_path, 'static', 'images')
        
        # Extract using mammoth (via current_engine helper)
        markdown_content = current_engine.extract_with_images(temp_path, images_dir)
        
        # Clean up
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        return jsonify({
            "message": "File processed",
            "markdown": markdown_content
        })
    except Exception as e:
        logging.error(f"Smart Canvas Upload Error: {e}")
        return jsonify({"error": str(e)}), 500
