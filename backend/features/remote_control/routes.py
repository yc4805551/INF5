"""
Remote Control API Routes

Provides HTTP endpoints for OpenClaw to control INF5's Fast Canvas.
"""
from flask import Blueprint, request, jsonify, send_file
from datetime import datetime
import logging
import io

from .auth import require_api_key
from .session_manager import session_manager
from .services import remote_service

logger = logging.getLogger(__name__)

remote_control_bp = Blueprint('remote_control', __name__)


def success_response(data: dict, message: str = None) -> dict:
    """Helper to create standardized success response."""
    response = {
        'status': 'success',
        'data': data,
        'timestamp': datetime.now().isoformat()
    }
    if message:
        response['message'] = message
    return response


def error_response(code: str, message: str, status_code: int = 400) -> tuple:
    """Helper to create standardized error response."""
    return jsonify({
        'status': 'error',
        'error': {
            'code': code,
            'message': message
        },
        'timestamp': datetime.now().isoformat()
    }), status_code


# ==================== Health & Info ====================

@remote_control_bp.route('/health', methods=['GET'])
@require_api_key
def health_check():
    """Health check endpoint."""
    return jsonify(success_response({
        'status': 'healthy',
        'version': '1.0.0',
        'service': 'Remote Control API'
    }))


@remote_control_bp.route('/capabilities', methods=['GET'])
@require_api_key
def list_capabilities():
    """List all available capabilities."""
    return jsonify(success_response({
        'capabilities': {
            'session_management': ['create', 'close', 'status'],
            'document_operations': ['create', 'import_docx', 'export_docx', 'export_smart_docx', 'get_content', 'update_content'],
            'ai_features': ['chat', 'smart_write', 'audit']
        }
    }))


# ==================== Session Management ====================

@remote_control_bp.route('/session/create', methods=['POST'])
@require_api_key
def create_session():
    """
    Create a new session.
    
    Request Body:
    {
        "session_name": "optional_name",
        "metadata": { ... }  // optional
    }
    """
    try:
        data = request.get_json() or {}
        metadata = data.get('metadata', {})
        
        # Add session name if provided
        if 'session_name' in data:
            metadata['session_name'] = data['session_name']
        
        result = session_manager.create_session(metadata)
        return jsonify(success_response(result, 'Session created successfully'))
    
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        return error_response('SESSION_CREATE_FAILED', str(e), 500)


@remote_control_bp.route('/session/<session_id>/status', methods=['GET'])
@require_api_key
def get_session_status(session_id):
    """Get session status and information."""
    try:
        session = session_manager.get_session(session_id)
        if not session:
            return error_response('SESSION_NOT_FOUND', f'Session {session_id} not found', 404)
        
        # Get document list
        documents = session_manager.list_documents(session_id)
        
        return jsonify(success_response({
            'session_id': session_id,
            'status': session['status'],
            'created_at': session['created_at'],
            'last_activity': session['last_activity'],
            'metadata': session['metadata'],
            'active_documents': documents
        }))
    
    except Exception as e:
        logger.error(f"Failed to get session status: {e}")
        return error_response('SESSION_STATUS_FAILED', str(e), 500)


@remote_control_bp.route('/session/<session_id>/close', methods=['POST'])
@require_api_key
def close_session(session_id):
    """Close a session and clean up resources."""
    try:
        success = session_manager.close_session(session_id)
        if not success:
            return error_response('SESSION_NOT_FOUND', f'Session {session_id} not found', 404)
        
        return jsonify(success_response({
            'session_id': session_id,
            'status': 'closed'
        }, 'Session closed successfully'))
    
    except Exception as e:
        logger.error(f"Failed to close session: {e}")
        return error_response('SESSION_CLOSE_FAILED', str(e), 500)


# ==================== Document Operations ====================

@remote_control_bp.route('/document/create', methods=['POST'])
@require_api_key
def create_document():
    """
    Create a document from Tiptap JSON.
    
    Request Body:
    {
        "session_id": "sess_xxx",
        "title": "Document Title",
        "content": { ... }  // Tiptap JSON
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return error_response('MISSING_DATA', 'Request body is required', 400)
        
        session_id = data.get('session_id')
        title = data.get('title', 'Untitled')
        content = data.get('content')
        
        if not session_id:
            return error_response('MISSING_SESSION_ID', 'session_id is required', 400)
        
        if not content:
            return error_response('MISSING_CONTENT', 'content is required', 400)
        
        # Verify session exists
        if not session_manager.get_session(session_id):
            return error_response('SESSION_NOT_FOUND', f'Session {session_id} not found', 404)
        
        doc_id = remote_service.create_document_from_json(session_id, title, content)
        
        return jsonify(success_response({
            'doc_id': doc_id,
            'title': title,
            'session_id': session_id
        }, 'Document created successfully'))
    
    except Exception as e:
        logger.error(f"Failed to create document: {e}")
        return error_response('DOCUMENT_CREATE_FAILED', str(e), 500)


@remote_control_bp.route('/document/import-docx', methods=['POST'])
@require_api_key
def import_docx():
    """
    Import a DOCX file.
    
    Request: multipart/form-data
    - file: DOCX file
    - session_id: Session ID
    """
    try:
        if 'file' not in request.files:
            return error_response('MISSING_FILE', 'No file provided', 400)
        
        session_id = request.form.get('session_id')
        if not session_id:
            return error_response('MISSING_SESSION_ID', 'session_id is required', 400)
        
        # Verify session exists
        if not session_manager.get_session(session_id):
            return error_response('SESSION_NOT_FOUND', f'Session {session_id} not found', 404)
        
        file = request.files['file']
        
        if file.filename == '':
            return error_response('EMPTY_FILENAME', 'Empty filename', 400)
        
        if not file.filename.lower().endswith('.docx'):
            return error_response('INVALID_FILE_TYPE', 'Only DOCX files are supported', 400)
        
        # Read file stream
        file_stream = io.BytesIO(file.read())
        
        # Import
        result = remote_service.import_docx(session_id, file_stream, file.filename)
        
        return jsonify(success_response(result, 'DOCX imported successfully'))
    
    except Exception as e:
        logger.error(f"Failed to import DOCX: {e}")
        return error_response('DOCX_IMPORT_FAILED', str(e), 500)


@remote_control_bp.route('/document/<doc_id>/export-docx', methods=['GET'])
@require_api_key
def export_docx(doc_id):
    """Export document as standard DOCX."""
    try:
        docx_stream = remote_service.export_docx(doc_id, 'standard')
        
        return send_file(
            docx_stream,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            as_attachment=True,
            download_name=f'{doc_id}_export.docx'
        )
    
    except ValueError as e:
        return error_response('DOCUMENT_NOT_FOUND', str(e), 404)
    except Exception as e:
        logger.error(f"Failed to export DOCX: {e}")
        return error_response('DOCX_EXPORT_FAILED', str(e), 500)


@remote_control_bp.route('/document/<doc_id>/export-smart-docx', methods=['GET'])
@require_api_key
def export_smart_docx(doc_id):
    """Export document as smart gov format DOCX."""
    try:
        docx_stream = remote_service.export_docx(doc_id, 'smart')
        
        return send_file(
            docx_stream,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            as_attachment=True,
            download_name=f'{doc_id}_smart_export.docx'
        )
    
    except ValueError as e:
        return error_response('DOCUMENT_NOT_FOUND', str(e), 404)
    except Exception as e:
        logger.error(f"Failed to export smart DOCX: {e}")
        return error_response('SMART_DOCX_EXPORT_FAILED', str(e), 500)


@remote_control_bp.route('/document/<doc_id>/content', methods=['GET'])
@require_api_key
def get_document_content(doc_id):
    """Get document content as Tiptap JSON."""
    try:
        doc = session_manager.get_document(doc_id)
        if not doc:
            return error_response('DOCUMENT_NOT_FOUND', f'Document {doc_id} not found', 404)
        
        return jsonify(success_response({
            'doc_id': doc_id,
            'title': doc['title'],
            'content': doc['content'],
            'created_at': doc['created_at'],
            'updated_at': doc['updated_at']
        }))
    
    except Exception as e:
        logger.error(f"Failed to get document content: {e}")
        return error_response('GET_CONTENT_FAILED', str(e), 500)


@remote_control_bp.route('/document/<doc_id>/content', methods=['PUT'])
@require_api_key
def update_document_content(doc_id):
    """
    Update document content.
    
    Request Body:
    {
        "content": { ... }  // Tiptap JSON
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'content' not in data:
            return error_response('MISSING_CONTENT', 'content is required', 400)
        
        success = session_manager.update_document(doc_id, data['content'])
        if not success:
            return error_response('DOCUMENT_NOT_FOUND', f'Document {doc_id} not found', 404)
        
        return jsonify(success_response({
            'doc_id': doc_id,
            'updated': True
        }, 'Document updated successfully'))
    
    except Exception as e:
        logger.error(f"Failed to update document: {e}")
        return error_response('UPDATE_CONTENT_FAILED', str(e), 500)


# ==================== AI Features ====================

@remote_control_bp.route('/ai/chat', methods=['POST'])
@require_api_key
def ai_chat():
    """
    Chat with knowledge base.
    
    Request Body:
    {
        "message": "Your question",
        "workspace": "inf_work",  // optional
        "history": [...],  // optional
        "context": "..."  // optional
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return error_response('MISSING_MESSAGE', 'message is required', 400)
        
        message = data['message']
        workspace = data.get('workspace')
        history = data.get('history', [])
        context = data.get('context')
        
        result = remote_service.chat_with_knowledge(message, workspace, history, context)
        
        return jsonify(success_response(result))
    
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        return error_response('CHAT_FAILED', str(e), 500)


@remote_control_bp.route('/ai/smart-write', methods=['POST'])
@require_api_key
def ai_smart_write():
    """
    Generate content using knowledge base.
    
    Request Body:
    {
        "prompt": "Your writing prompt",
        "workspace": "inf_work"  // optional
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'prompt' not in data:
            return error_response('MISSING_PROMPT', 'prompt is required', 400)
        
        prompt = data['prompt']
        workspace = data.get('workspace')
        
        result = remote_service.smart_write(prompt, workspace)
        
        return jsonify(success_response(result))
    
    except Exception as e:
        logger.error(f"Smart write failed: {e}")
        return error_response('SMART_WRITE_FAILED', str(e), 500)


@remote_control_bp.route('/ai/audit', methods=['POST'])
@require_api_key
def ai_audit():
    """
    Audit a document.
    
    Request Body:
    {
        "doc_id": "doc_xxx",
        "rules": "Custom audit rules"  // optional
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'doc_id' not in data:
            return error_response('MISSING_DOC_ID', 'doc_id is required', 400)
        
        doc_id = data['doc_id']
        rules = data.get('rules')
        
        result = remote_service.audit_document(doc_id, rules)
        
        return jsonify(success_response(result))
    
    except ValueError as e:
        return error_response('DOCUMENT_NOT_FOUND', str(e), 404)
    except Exception as e:
        logger.error(f"Audit failed: {e}")
        return error_response('AUDIT_FAILED', str(e), 500)
