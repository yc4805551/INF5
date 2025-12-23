from flask import Blueprint, request, jsonify, Response, stream_with_context
import logging
from core.proxies import (
    call_gemini_openai_proxy, stream_gemini_openai_proxy,
    call_openai_proxy, stream_openai_proxy,
    call_deepseek_proxy, stream_deepseek_proxy,
    call_ali_proxy, stream_ali_proxy
)

common_bp = Blueprint('common', __name__)

@common_bp.route('/generate', methods=['POST']) 
def handle_generate(): 
    try: 
        data = request.get_json() 
        provider = data.get('provider') 
        logging.info(f"Received non-stream generation request, Provider: {provider}") 
        
        if provider == 'gemini': 
            return call_gemini_openai_proxy(data)
        elif provider == 'openai': 
            return call_openai_proxy(data) 
        elif provider == 'deepseek': 
            return call_deepseek_proxy(data) 
        elif provider == 'ali': 
            return call_ali_proxy(data) 
        else: 
            return jsonify({"error": f"Unsupported provider: {provider}"}), 400 
    except Exception as e: 
        logging.error(f"API /generate error: {e}") 
        return jsonify({"error": str(e)}), 500 

@common_bp.route('/generate-stream', methods=['POST']) 
def handle_generate_stream(): 
    try: 
        data = request.get_json() 
        provider = data.get('provider') 
        sys_inst = data.get('systemInstruction') 
        user_prompt = data.get('userPrompt') 
        history = data.get('history', []) 
        
        logging.info(f"Received stream generation request, Provider: {provider}") 

        if provider == 'gemini': 
            return Response(stream_with_context(stream_gemini_openai_proxy(user_prompt, sys_inst, history)), content_type='text/plain') 
        elif provider == 'openai': 
            return Response(stream_with_context(stream_openai_proxy(user_prompt, sys_inst, history)), content_type='text/plain') 
        elif provider == 'deepseek': 
            return Response(stream_with_context(stream_deepseek_proxy(user_prompt, sys_inst, history)), content_type='text/plain') 
        elif provider == 'ali': 
            return Response(stream_with_context(stream_ali_proxy(user_prompt, sys_inst, history)), content_type='text/plain') 
        else: 
            return Response(stream_with_context([f"[Error: Unsupported provider: {provider}]"]), content_type='text/plain') 
    except Exception as e: 
        return Response(stream_with_context([f"[Internal Error: {str(e)}]"]), content_type='text/plain')
