from flask import Blueprint, request, jsonify
from .services import advisor_service

advisor_bp = Blueprint('advisor', __name__)

@advisor_bp.route('/suggestions', methods=['POST'])
def get_suggestions():
    data = request.json
    selected_text = data.get('selectedText', '')
    context_text = data.get('contextText', '')
    model_config = data.get('modelConfig', {}) # Frontend passes partial config

    try:
        suggestions = advisor_service.generate_suggestions(selected_text, context_text, model_config)
        return jsonify({"status": "success", "suggestions": suggestions})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@advisor_bp.route('/copilot', methods=['POST'])
def chat_copilot():
    """
    Unified Copilot Endpoint.
    Handles Chat & Audit Triggers.
    """
    from .copilot import copilot_service
    import asyncio
    
    data = request.json or {}
    
    try:
        # Run async service method in sync route
        result = asyncio.run(copilot_service.handle_request(data))
        return jsonify(result)
    except Exception as e:
        return jsonify({"type": "error", "content": str(e)}), 500
