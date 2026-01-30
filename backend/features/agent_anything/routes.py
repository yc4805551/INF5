from flask import Blueprint, request, jsonify, Response
import json
from .services import perform_anything_audit, get_anything_workspaces, chat_with_anything, generate_content_with_knowledge

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
    Expects JSON: { "message": "...", "history": [...], "workspace_slug": "..." (optional) }
    Returns: { "response": "...", "sources": [...] }
    """
    data = request.json
    message = data.get('message', '')
    history = data.get('history', [])
    workspace_slug = data.get('workspace_slug')  # NEW: Accept slug from frontend
    
    try:
        result = chat_with_anything(message, history, workspace_slug)
        # result is now { 'response': '...', 'sources': [...] }
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@agent_anything_bp.route('/workspaces', methods=['GET'])
def list_workspaces():
    """List available AnythingLLM workspaces in frontend-friendly format"""
    try:
        workspaces = get_anything_workspaces()
        # Format for frontend: [{ id: 'anything-llm-inf_knowledge', name: '🤖 inf_knowledge', slug: 'inf-knowledge' }]
        formatted = [{
            'id': f'anything-llm-{ws["name"]}',
            'name': f'🤖 {ws["name"]}',
            'slug': ws['slug']
        } for ws in workspaces]
        return jsonify({'workspaces': formatted})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@agent_anything_bp.route('/smart-write', methods=['POST'])
def smart_write():
    """
    Endpoint for Knowledge-Driven Smart Writing.
    Expects: { "prompt": "..." }
    """
    data = request.json
    prompt = data.get('prompt')
    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400
        
    try:
        result = generate_content_with_knowledge(prompt)
        # Use simplejson/json dumps to avoiding escaping unicode
        return Response(json.dumps(result, ensure_ascii=False), mimetype='application/json')
    except Exception as e:
        return jsonify({"error": str(e)}), 500
