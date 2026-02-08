"""
Authentication middleware for Remote Control API
"""
import os
import logging
from functools import wraps
from flask import request, jsonify

logger = logging.getLogger(__name__)

def require_api_key(f):
    """
    Decorator to require API Key authentication for Remote Control endpoints.
    
    Usage:
        @require_api_key
        def protected_route():
            pass
    
    API Key should be provided in the 'X-API-Key' header.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        
        # Check if Remote Control is enabled
        if not os.getenv('OPENCLAW_ENABLED', 'false').lower() == 'true':
            logger.warning("Remote Control API is disabled")
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 'API_DISABLED',
                    'message': 'Remote Control API is not enabled'
                }
            }), 503
        
        # Validate API Key
        expected_key = os.getenv('OPENCLAW_API_KEY')
        if not expected_key:
            logger.error("OPENCLAW_API_KEY not configured")
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 'SERVER_MISCONFIGURED',
                    'message': 'API Key not configured on server'
                }
            }), 500
        
        if not api_key:
            logger.warning("Missing API Key in request")
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 'MISSING_API_KEY',
                    'message': 'X-API-Key header is required'
                }
            }), 401
        
        if api_key != expected_key:
            logger.warning(f"Invalid API Key attempt: {api_key[:8]}...")
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 'INVALID_API_KEY',
                    'message': 'Invalid API Key'
                }
            }), 401
        
        # API Key is valid, proceed
        logger.info(f"API Key validated for {request.endpoint}")
        return f(*args, **kwargs)
    
    return decorated_function


def generate_api_key(length: int = 32) -> str:
    """
    Generate a secure random API key.
    
    Args:
        length: Length of the API key (default: 32)
    
    Returns:
        A secure random API key string
    """
    import secrets
    import string
    
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


if __name__ == '__main__':
    # Generate a sample API key
    print("Sample API Key:", generate_api_key())
