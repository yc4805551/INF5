import os
import logging
import requests
import json
from flask import jsonify, Response, stream_with_context

# Configs
# Configs
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("VITE_GEMINI_API_KEY")
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
GEMINI_MODEL = os.getenv("GEMINI_MODEL") or os.getenv("VITE_GEMINI_MODEL") or "gemini-2.0-flash-exp"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("VITE_OPENAI_API_KEY")
OPENAI_TARGET_URL = os.getenv("OPENAI_TARGET_URL") or os.getenv("VITE_OPENAI_TARGET_URL") or "https://api.chatanywhere.tech"
OPENAI_MODEL = os.getenv("OPENAI_MODEL") or os.getenv("VITE_OPENAI_MODEL") or "gpt-3.5-turbo"

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY") or os.getenv("VITE_DEEPSEEK_API_KEY")
DEEPSEEK_ENDPOINT = os.getenv("DEEPSEEK_ENDPOINT") or os.getenv("VITE_DEEPSEEK_ENDPOINT") or "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL") or os.getenv("VITE_DEEPSEEK_MODEL") or "deepseek-chat"

ALI_API_KEY = os.getenv("ALI_API_KEY") or os.getenv("VITE_ALI_API_KEY")
ALI_TARGET_URL = os.getenv("ALI_TARGET_URL") or os.getenv("VITE_ALI_TARGET_URL") or "https://dashscope.aliyuncs.com/compatible-mode"
ALI_MODEL = os.getenv("ALI_MODEL") or os.getenv("VITE_ALI_MODEL") or "qwen-plus"

# --- 1. Gemini (OpenAI Compatible) ---
def call_gemini_openai_proxy(data):
    # Extract config from frontend (if provided) or use environment variables
    model_config = data.get('modelConfig', {})
    api_key = model_config.get('apiKey') or GEMINI_API_KEY
    model = model_config.get('model') or GEMINI_MODEL
    
    if not api_key: 
        return jsonify({"error": "GEMINI_API_KEY 未设置"}), 500 
    
    base_url = GEMINI_BASE_URL.rstrip('/')
    url = f"{base_url}/chat/completions"
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'}
    
    messages = []
    if data.get('systemInstruction'):
        messages.append({"role": "system", "content": data.get('systemInstruction')})
    for item in data.get('history', []):
        if item.get('role') and item.get('parts'):
            messages.append({"role": item.get('role'), "content": item.get('parts')[0].get('text')})
    messages.append({"role": "user", "content": data.get('userPrompt')})
    
    payload = {"model": model, "messages": messages, "temperature": 0.7}
    
    # Add response_format for JSON mode if requested
    if data.get('jsonResponse'):
        payload['response_format'] = {'type': 'json_object'}
    
    response = requests.post(url, headers=headers, json=payload, timeout=180)
    if response.status_code != 200:
        logging.error(f"Gemini Proxy Error ({response.status_code}): {response.text}")
        response.raise_for_status()
        
    response_data = response.json()
    if 'choices' in response_data and len(response_data['choices']) > 0:
        content = response_data['choices'][0]['message']['content']
        return Response(content, mimetype='text/plain; charset=utf-8')
    raise ValueError("Gemini 响应格式无效")

def stream_gemini_openai_proxy(user_prompt, system_instruction, history, model_config=None):
    # Extract config from parameter or use environment variables
    if model_config is None:
        model_config = {}
    api_key = model_config.get('apiKey') or GEMINI_API_KEY
    model = model_config.get('model') or GEMINI_MODEL
    
    if not api_key: 
        yield "[错误: GEMINI_API_KEY 未设置]"
        return

    base_url = GEMINI_BASE_URL.rstrip('/')
    url = f"{base_url}/chat/completions"
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'}
    
    messages = []
    if system_instruction: messages.append({"role": "system", "content": system_instruction})
    for item in history:
        if item.get('role') and item.get('parts'):
            messages.append({"role": item.get('role'), "content": item.get('parts')[0].get('text')})
    messages.append({"role": "user", "content": user_prompt})
    
    payload = {"model": model, "messages": messages, "temperature": 0.7, "stream": True}
    
    try:
        with requests.post(url, headers=headers, json=payload, stream=True, timeout=180) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if line:
                    line_str = line.decode('utf-8').strip()
                    if line_str.startswith('data: '):
                        line_str = line_str[6:]
                        if line_str == '[DONE]': break
                        try:
                            chunk = json.loads(line_str)
                            if chunk.get('choices') and chunk['choices'][0].get('delta', {}).get('content'):
                                yield chunk['choices'][0]['delta']['content']
                        except: pass
    except Exception as e:
        logging.error(f"Gemini Stream Error: {e}")
        yield f"[Proxy Error: {str(e)}]"

# --- 2. OpenAI (and FREE) ---
def call_openai_proxy(data):
    # Extract config from frontend (for 'free' or 'openai' provider)
    model_config = data.get('modelConfig', {})
    api_key = model_config.get('apiKey') or OPENAI_API_KEY
    endpoint = model_config.get('endpoint') or f"{OPENAI_TARGET_URL}/v1/chat/completions"
    model = model_config.get('model') or OPENAI_MODEL
    
    if not api_key:
        return jsonify({"error": "API Key not provided"}), 400
    
    # Ensure endpoint ends with /chat/completions
    if not endpoint.endswith('/chat/completions'):
        endpoint = endpoint.rstrip('/') + '/chat/completions'
    
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'}
    messages = []
    if data.get('systemInstruction'): messages.append({"role": "system", "content": data.get('systemInstruction')})
    for item in data.get('history', []):
        if item.get('role') and item.get('parts'):
            role = item.get('role')
            if role == 'model': role = 'assistant'
            messages.append({"role": role, "content": item.get('parts')[0].get('text')})
    messages.append({"role": "user", "content": data.get('userPrompt')})
    payload = {"model": model, "messages": messages, "temperature": 0.7}

    # Add response_format for JSON mode if requested
    if data.get('jsonResponse'):
        payload['response_format'] = {'type': 'json_object'}
    response = requests.post(endpoint, headers=headers, json=payload, timeout=180)
    response.raise_for_status()
    # IMPORTANT: Return plain text, NOT jsonify() to avoid double-encoding
    content = response.json()['choices'][0]['message']['content']
    return Response(content, mimetype='text/plain; charset=utf-8')

def stream_openai_proxy(user_prompt, system_instruction, history, model_config=None):
    # Extract config from parameter (for 'free' or 'openai' provider)
    if model_config is None:
        model_config = {}
    api_key = model_config.get('apiKey') or OPENAI_API_KEY
    endpoint = model_config.get('endpoint') or f"{OPENAI_TARGET_URL}/v1/chat/completions"
    model = model_config.get('model') or OPENAI_MODEL
    
    if not api_key:
        yield "[Error: API Key not provided]"
        return
    
    # Ensure endpoint ends with /chat/completions
    if not endpoint.endswith('/chat/completions'):
        endpoint = endpoint.rstrip('/') + '/chat/completions'
    
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'}
    messages = []
    if system_instruction: messages.append({"role": "system", "content": system_instruction})
    for item in history:
        if item.get('role') and item.get('parts'):
            role = item.get('role')
            if role == 'model': role = 'assistant'
            messages.append({"role": role, "content": item.get('parts')[0].get('text')})
    messages.append({"role": "user", "content": user_prompt})
    payload = {"model": model, "messages": messages, "temperature": 0.7, "stream": True}
    try:
        with requests.post(endpoint, headers=headers, json=payload, stream=True, timeout=180) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if line:
                    line_str = line.decode('utf-8').strip()
                    if line_str.startswith('data: '):
                        line_str = line_str[6:]
                        if line_str == '[DONE]': break
                        try:
                            chunk = json.loads(line_str)
                            if chunk.get('choices') and chunk['choices'][0].get('delta', {}).get('content'):
                                yield chunk['choices'][0]['delta']['content']
                        except: pass
    except Exception as e: yield f"[Proxy Error: {str(e)}]"

# --- 3. DeepSeek ---
def call_deepseek_proxy(data):
    # Extract config from frontend (if provided) or use environment variables
    model_config = data.get('modelConfig', {})
    api_key = model_config.get('apiKey') or DEEPSEEK_API_KEY
    endpoint = model_config.get('endpoint') or DEEPSEEK_ENDPOINT
    model = model_config.get('model') or DEEPSEEK_MODEL
    
    if not api_key:
        return jsonify({"error": "DEEPSEEK_API_KEY 未设置"}), 500
    
    url = endpoint
    if not url.endswith('/chat/completions'):
        url = url.rstrip('/') + '/chat/completions'
        
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'}
    messages = []
    if data.get('systemInstruction'): messages.append({"role": "system", "content": data.get('systemInstruction')})
    for item in data.get('history', []):
        if item.get('role') and item.get('parts'):
            role = item.get('role')
            if role == 'model': role = 'assistant'
            messages.append({"role": role, "content": item.get('parts')[0].get('text')})
    messages.append({"role": "user", "content": data.get('userPrompt')})
    payload = {"model": model, "messages": messages, "temperature": 0.7}

    # Add response_format for JSON mode if requested
    if data.get('jsonResponse'):
        payload['response_format'] = {'type': 'json_object'}
    response = requests.post(url, headers=headers, json=payload, timeout=180)
    response.raise_for_status()
    content = response.json()['choices'][0]['message']['content']
    return Response(content, mimetype='text/plain; charset=utf-8')

def stream_deepseek_proxy(user_prompt, system_instruction, history, model_config=None):
    # Extract config from parameter or use environment variables
    if model_config is None:
        model_config = {}
    api_key = model_config.get('apiKey') or DEEPSEEK_API_KEY
    endpoint = model_config.get('endpoint') or DEEPSEEK_ENDPOINT
    model = model_config.get('model') or DEEPSEEK_MODEL
    
    if not api_key:
        yield "[Error: DEEPSEEK_API_KEY 未设置]"
        return
    
    url = endpoint
    if not url.endswith('/chat/completions'):
        url = url.rstrip('/') + '/chat/completions'

    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'}
    messages = []
    if system_instruction: messages.append({"role": "system", "content": system_instruction})
    for item in history:
        if item.get('role') and item.get('parts'):
            role = item.get('role')
            if role == 'model': role = 'assistant'
            messages.append({"role": role, "content": item.get('parts')[0].get('text')})
    messages.append({"role": "user", "content": user_prompt})
    payload = {"model": model, "messages": messages, "temperature": 0.7, "stream": True}
    try:
        with requests.post(url, headers=headers, json=payload, stream=True, timeout=180) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if line:
                    line_str = line.decode('utf-8').strip()
                    if line_str.startswith('data: '):
                        line_str = line_str[6:]
                        if line_str == '[DONE]': break
                        try:
                            chunk = json.loads(line_str)
                            if chunk.get('choices') and chunk['choices'][0].get('delta', {}).get('content'):
                                yield chunk['choices'][0]['delta']['content']
                        except: pass
    except Exception as e: yield f"[Proxy Error: {str(e)}]"

# --- 4. Ali ---
def call_ali_proxy(data):
    # Extract config from frontend (if provided) or use environment variables
    model_config = data.get('modelConfig', {})
    api_key = model_config.get('apiKey') or ALI_API_KEY
    target_url = model_config.get('endpoint') or ALI_TARGET_URL
    model = model_config.get('model') or ALI_MODEL
    
    if not api_key:
        return jsonify({"error": "ALI_API_KEY 未设置"}), 500
    
    # Handle endpoint formatting robustly
    url = target_url.rstrip('/')
    if not url.endswith('/chat/completions'):
        if not url.endswith('/v1'):
            url = f"{url}/v1"
        url = f"{url}/chat/completions"
    
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'}
    messages = []
    if data.get('systemInstruction'): messages.append({"role": "system", "content": data.get('systemInstruction')})
    for item in data.get('history', []):
        if item.get('role') and item.get('parts'):
            role = item.get('role')
            if role == 'model': role = 'assistant'
            messages.append({"role": role, "content": item.get('parts')[0].get('text')})
    messages.append({"role": "user", "content": data.get('userPrompt')})
    payload = {"model": model, "messages": messages, "temperature": 0.7}

    # Add response_format for JSON mode if requested
    if data.get('jsonResponse'):
        payload['response_format'] = {'type': 'json_object'}
    response = requests.post(url, headers=headers, json=payload, timeout=180)
    response.raise_for_status()
    # Ali returns OpenAI-compatible format
    content = response.json()['choices'][0]['message']['content']
    return Response(content, mimetype='text/plain; charset=utf-8')

def stream_ali_proxy(user_prompt, system_instruction, history, model_config=None):
    # Extract config from parameter or use environment variables
    if model_config is None:
        model_config = {}
    api_key = model_config.get('apiKey') or ALI_API_KEY
    target_url = model_config.get('endpoint') or ALI_TARGET_URL
    model = model_config.get('model') or ALI_MODEL
    
    if not api_key:
        yield "[Error: ALI_API_KEY 未设置]"
        return
    
    # Handle endpoint formatting robustly
    url = target_url.rstrip('/')
    if not url.endswith('/chat/completions'):
        if not url.endswith('/v1'):
            url = f"{url}/v1"
        url = f"{url}/chat/completions"
    
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'}
    messages = []
    if system_instruction: messages.append({"role": "system", "content": system_instruction})
    for item in history:
        if item.get('role') and item.get('parts'):
            role = item.get('role')
            if role == 'model': role = 'assistant'
            messages.append({"role": role, "content": item.get('parts')[0].get('text')})
    messages.append({"role": "user", "content": user_prompt})
    payload = {"model": model, "messages": messages, "temperature": 0.7, "stream": True}
    try:
        with requests.post(url, headers=headers, json=payload, stream=True, timeout=180) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if line:
                    line_str = line.decode('utf-8').strip()
                    if line_str.startswith('data: '):
                        line_str = line_str[6:]
                        if line_str == '[DONE]': break
                        try:
                            chunk = json.loads(line_str)
                            if chunk.get('choices') and chunk['choices'][0].get('delta', {}).get('content'):
                                yield chunk['choices'][0]['delta']['content']
                        except: pass
    except Exception as e: yield f"[Proxy Error: {str(e)}]"
