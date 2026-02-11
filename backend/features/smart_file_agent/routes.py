
from flask import Blueprint, request, Response, stream_with_context
from .services import SmartFileAgent
from .config import OCR_MODEL_PROVIDER

smart_file_agent_bp = Blueprint('smart_file_agent', __name__)

@smart_file_agent_bp.route('/process', methods=['POST'])
def process_files_route():
    # 1. Get Files
    files = request.files.getlist('files')
    if not files:
        return {"error": "No files provided"}, 400

    # 2. Get Config (Cleaning Model)
    # Passed as JSON string in form-data 'config' or just use global
    import json
    cleaning_model_config = None
    if 'config' in request.form:
        try:
            cleaning_model_config = json.loads(request.form['config'])
        except:
            pass
            
    ocr_provider = None
    if cleaning_model_config:
        ocr_provider = cleaning_model_config.get('ocrProvider')

    # 3. Initialize Agent
    agent = SmartFileAgent(
        use_llm_clean=False, # Default OFF for now unless UI explicitly requests
        cleaning_model_config=cleaning_model_config,
        ocr_provider=ocr_provider
    )

    # 4. Stream Response
    return Response(
        stream_with_context(agent.process_files(files)),
        mimetype='application/x-ndjson'
    )
