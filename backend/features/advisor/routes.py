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
