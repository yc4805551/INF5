from flask import Blueprint, request, jsonify
from .services import smart_filler_service
import logging
import traceback
import os

logger = logging.getLogger(__name__)

smart_filler_bp = Blueprint('smart_filler', __name__)

def log_error_to_file(e):
    try:
        # Write to backend root (backend/)
        # Current file: backend/features/smart_filler/routes.py
        # root is 3 levels up
        log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "last_error.log")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(str(e) + "\n" + traceback.format_exc())
    except Exception as ie:
        logger.error(f"Failed to write error log: {ie}")

@smart_filler_bp.route('/upload-source', methods=['POST'])
def upload_source():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    try:
        # Use new generic parse_source
        result = smart_filler_service.parse_source(file)
        return jsonify(result)
    except Exception as e:
        log_error_to_file(e)
        return jsonify({"error": str(e)}), 500

@smart_filler_bp.route('/upload-excel', methods=['POST'])
def upload_excel():
    """Deprecated: Use /upload-source instead. Kept for backward compatibility."""
    return upload_source()

@smart_filler_bp.route('/status', methods=['GET'])
def get_status():
    try:
        from core.services import current_engine
        # Use the same log_debug logic if possible, or append explicitly
        # We'll just write to the log file manually to match tools.py
        try:
             base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
             log_path = os.path.join(base_dir, "smart_filler_debug.log")
             import datetime
             ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
             with open(log_path, "a", encoding="utf-8") as f:
                 f.write(f"[{ts}] [ROUTE] Status Check - Engine ID: {id(current_engine)}\n")
        except:
             pass

        status = smart_filler_service.get_current_status()
        return jsonify(status)
    except Exception as e:
        log_error_to_file(e)
        return jsonify({"error": str(e)}), 500

@smart_filler_bp.route('/recommendations', methods=['GET'])
def get_recommendations():
    try:
        result = smart_filler_service.get_recommendations()
        return jsonify(result)
    except Exception as e:
        log_error_to_file(e)
        return jsonify({"error": str(e)}), 500

@smart_filler_bp.route('/execute-fill', methods=['POST'])
def execute_fill():
    data = request.json
    table_index = data.get('table_index')
    if table_index is None:
        return jsonify({"error": "Missing table_index"}), 400
        
    try:
        result = smart_filler_service.fill_table(table_index)
        return jsonify(result)
    except ValueError as ve:
        # Expected error (e.g. no Excel), return 400
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        log_error_to_file(e)
        return jsonify({"error": str(e)}), 500

@smart_filler_bp.route('/agent-task', methods=['POST'])
def agent_task():
    data = request.json
    instruction = data.get('instruction')
    model_config = data.get('modelConfig') # Pass generic config
    plan = data.get('plan') # Optional user-modified plan
    
    if not instruction:
        return jsonify({"error": "Missing instruction"}), 400

    try:
        # Pass model_config to service
        result = smart_filler_service.run_agent_task(instruction, model_config, plan)
        return jsonify(result)
    except Exception as e:
        log_error_to_file(e)
        return jsonify({"error": str(e)}), 500

@smart_filler_bp.route('/plan', methods=['POST'])
def generate_plan():
    data = request.json
    instruction = data.get('instruction')
    model_config = data.get('modelConfig')
    
    if not instruction:
        return jsonify({"error": "Missing instruction"}), 400

    try:
        result = smart_filler_service.generate_plan(instruction, model_config)
        return jsonify(result)
    except Exception as e:
        log_error_to_file(e)
        return jsonify({"error": str(e)}), 500

@smart_filler_bp.route('/logs', methods=['GET'])
def get_debug_logs():
    try:
        # Read from smart_filler_debug.log (we will ensure service writes to this)
        # Or just read last_error.log and general logs
        # Try both logs
        # routes.py is in backend/features/smart_filler/
        # Need 3 levels up for Backend Root
        log_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        debug_log_path = os.path.join(log_dir, "smart_filler_debug.log")
        error_log_path = os.path.join(log_dir, "last_error.log")
        
        content = ""
        
        if os.path.exists(debug_log_path):
            with open(debug_log_path, "r", encoding="utf-8") as f:
                content += "=== DEBUG LOG ===\n" + f.read()[-3000:] + "\n\n"
                
        if os.path.exists(error_log_path):
            with open(error_log_path, "r", encoding="utf-8") as f:
                content += "=== LAST ERROR ===\n" + f.read() + "\n"
        
        if not content:
            content = "No logs available."
            
        return jsonify({"logs": content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@smart_filler_bp.route('/debug/state', methods=['GET'])
def debug_filler_state():
    from core.services import current_engine
    try:
        data = {
            "engine_id": id(current_engine),
            "doc_preview": [p.text[:50] for p in current_engine.doc.paragraphs[:5]] if current_engine.doc else None,
            "has_doc": bool(current_engine.doc),
            "original_path": getattr(current_engine, 'original_path', 'Not Set')
        }
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
