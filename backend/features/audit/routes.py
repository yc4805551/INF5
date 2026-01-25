from flask import request, jsonify, Response
from . import audit_bp
from .services import perform_audit, perform_audit_stream
import logging

@audit_bp.route('/analyze', methods=['POST'])
def audit_analyze():
    """
    API Endpoint to trigger document audit.
    Requires 'Target' (loaded in Canvas) and 'Source' (loaded in References).
    Payload: { "rules": "...", "model_config": {...}, "stream": true }
    """
    import asyncio
    try:
        data = request.get_json() or {}
        logging.info(f"Received Audit Analyze Request (Stream={data.get('stream')})")
        
        # Check for Streaming Mode
        if data.get("stream"):
             return Response(perform_audit_stream(data), mimetype='text/plain')

        # Run async logic in a synchronous wrapper
        result = asyncio.run(perform_audit(data))
        
        if "error" in result:
             logging.error(f"Audit failed: {result['error']}")
             return jsonify(result), 400
             
        return jsonify(result)
    except Exception as e:
        logging.error(f"Audit Internal Error: {e}")
        return jsonify({"error": str(e)}), 500

@audit_bp.route('/realtime', methods=['POST'])
def audit_realtime():
    """
    API Endpoint for Lightweight Realtime Proofreading.
    Payload: { "content": "...", "source": "...", "model_config": {...} }
    """
    import asyncio
    from .services import perform_realtime_check
    try:
        data = request.get_json() or {}
        # logging.info(f"Received Realtime Check Request (len={len(data.get('content',''))})")
        
        # Directly call lightweight service
        result = asyncio.run(perform_realtime_check(data))
        
        return jsonify(result)
    except Exception as e:
        logging.error(f"Realtime Check Error: {e}")
        return jsonify({"error": str(e)}), 500
