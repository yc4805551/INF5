from flask import Blueprint, request, jsonify
from .services import perform_anything_audit, get_anything_workspaces, chat_with_anything

agent_anything_bp = Blueprint('agent_anything', __name__)

@agent_anything_bp.route('/audit', methods=['POST'])
def audit_endpoint():
    """
    Endpoint for Document Audit via AnythingLLM.
    Expects JSON: { "target_text": "...", "source_text": "...", "rules": "..." }
    """
    data = request.json
    target_text = data.get('target_text', '')
    source_context = data.get('source_text', '')
    rules = data.get('rules', '')
    
    # Optional: Allow frontend to specify workspace if we support multiple
    # workspace_slug = data.get('workspace', 'inf_knowledge') 

    try:
        result = perform_anything_audit(target_text, source_context, rules)
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500

@agent_anything_bp.route('/chat', methods=['POST'])
def chat_endpoint():
    """
    Endpoint for Chat via AnythingLLM (Knowledge Base Chat).
    Expects JSON: { "message": "...", "history": [...] }
    """
    data = request.json
    message = data.get('message', '')
    history = data.get('history', [])
    
    try:
        response_text = chat_with_anything(message, history)
        return jsonify({"response": response_text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@agent_anything_bp.route('/workspaces', methods=['GET'])
def list_workspaces():
    """List available workspaces"""
    try:
        workspaces = get_anything_workspaces()
        return jsonify(workspaces)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
