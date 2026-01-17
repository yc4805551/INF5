import os
import logging
import requests
import json
from flask import jsonify, Response, stream_with_context

# Configs
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("VITE_GEMINI_API_KEY")
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-exp")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "dummy-key-for-proxy")
OPENAI_TARGET_URL = os.getenv("OPENAI_TARGET_URL", "https://api.chatanywhere.tech")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "dummy-key-for-proxy")
DEEPSEEK_ENDPOINT = os.getenv("DEEPSEEK_ENDPOINT", "https://api.deepseek.com/v1/chat/completions")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

ALI_API_KEY = os.getenv("ALI_API_KEY")
ALI_TARGET_URL = os.getenv("ALI_TARGET_URL", "https://dashscope.aliyuncs.com/compatible-mode")
ALI_MODEL = os.getenv("ALI_MODEL", "qwen-plus")

# --- 1. Gemini (OpenAI Compatible) ---
def call_gemini_openai_proxy(data):
    if not GEMINI_API_KEY: return jsonify({"error": "GEMINI_API_KEY 未设置"}), 500 
    base_url = GEMINI_BASE_URL.rstrip('/')
    url = f"{base_url}/chat/completions"
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {GEMINI_API_KEY}'}
    
    messages = []
    if data.get('systemInstruction'):
        messages.append({"role": "system", "content": data.get('systemInstruction')})
    for item in data.get('history', []):
        if item.get('role') and item.get('parts'):
            messages.append({"role": item.get('role'), "content": item.get('parts')[0].get('text')})
    messages.append({"role": "user", "content": data.get('userPrompt')})
    
    payload = {"model": GEMINI_MODEL, "messages": messages, "temperature": 0.7}
    
    response = requests.post(url, headers=headers, json=payload, timeout=180)
    if response.status_code != 200:
        logging.error(f"Gemini Proxy Error ({response.status_code}): {response.text}")
        response.raise_for_status()
        
    response_data = response.json()
    if 'choices' in response_data and len(response_data['choices']) > 0:
        return jsonify(response_data['choices'][0]['message']['content']) # Consistent with previous
    raise ValueError("Gemini 响应格式无效")

def stream_gemini_openai_proxy(user_prompt, system_instruction, history):
    if not GEMINI_API_KEY: 
        yield "[错误: GEMINI_API_KEY 未设置]"
        return

    base_url = GEMINI_BASE_URL.rstrip('/')
    url = f"{base_url}/chat/completions"
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {GEMINI_API_KEY}'}
    
    messages = []
    if system_instruction: messages.append({"role": "system", "content": system_instruction})
    for item in history:
        if item.get('role') and item.get('parts'):
            messages.append({"role": item.get('role'), "content": item.get('parts')[0].get('text')})
    messages.append({"role": "user", "content": user_prompt})
    
    payload = {"model": GEMINI_MODEL, "messages": messages, "temperature": 0.7, "stream": True}
    
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

# --- 2. OpenAI ---
def call_openai_proxy(data):
    url = f"{OPENAI_TARGET_URL}/v1/chat/completions"
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {OPENAI_API_KEY}'}
    messages = []
    if data.get('systemInstruction'): messages.append({"role": "system", "content": data.get('systemInstruction')})
    for item in data.get('history', []):
        if item.get('role') and item.get('parts'):
            messages.append({"role": item.get('role'), "content": item.get('parts')[0].get('text')})
    messages.append({"role": "user", "content": data.get('userPrompt')})
    payload = {"model": OPENAI_MODEL, "messages": messages, "temperature": 0.7}
    response = requests.post(url, headers=headers, json=payload, timeout=180)
    response.raise_for_status()
    # Return content string directly to match original structure? 
    # Original used: Response(..., content_type='application/json') containing just the content string?
    # No, usually OpenAI returns JSON object. But here we just want the text content for the frontend?
    # The original _call_openai_proxy returned Response(content_string, content_type='application/json'). 
    # Frontend likely expects just the string in the body or a JSON wrapper.
    # The Gemini one returns jsonify(content), which wraps it in quotes in the body but header is app/json.
    # Let's standardize to returning the content string.
    return jsonify(response.json()['choices'][0]['message']['content'])

def stream_openai_proxy(user_prompt, system_instruction, history):
    url = f"{OPENAI_TARGET_URL}/v1/chat/completions"
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {OPENAI_API_KEY}'}
    messages = []
    if system_instruction: messages.append({"role": "system", "content": system_instruction})
    for item in history:
        if item.get('role') and item.get('parts'):
            messages.append({"role": item.get('role'), "content": item.get('parts')[0].get('text')})
    messages.append({"role": "user", "content": user_prompt})
    payload = {"model": OPENAI_MODEL, "messages": messages, "temperature": 0.7, "stream": True}
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

# --- 3. DeepSeek ---
def call_deepseek_proxy(data):
    url = DEEPSEEK_ENDPOINT
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {DEEPSEEK_API_KEY}'}
    messages = []
    if data.get('systemInstruction'): messages.append({"role": "system", "content": data.get('systemInstruction')})
    for item in data.get('history', []):
        if item.get('role') and item.get('parts'):
            messages.append({"role": item.get('role'), "content": item.get('parts')[0].get('text')})
    messages.append({"role": "user", "content": data.get('userPrompt')})
    payload = {"model": DEEPSEEK_MODEL, "messages": messages, "temperature": 0.7}
    response = requests.post(url, headers=headers, json=payload, timeout=180)
    response.raise_for_status()
    return jsonify(response.json()['choices'][0]['message']['content'])

def stream_deepseek_proxy(user_prompt, system_instruction, history):
    url = DEEPSEEK_ENDPOINT
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {DEEPSEEK_API_KEY}'}
    messages = []
    if system_instruction: messages.append({"role": "system", "content": system_instruction})
    for item in history:
        if item.get('role') and item.get('parts'):
            messages.append({"role": item.get('role'), "content": item.get('parts')[0].get('text')})
    messages.append({"role": "user", "content": user_prompt})
    payload = {"model": DEEPSEEK_MODEL, "messages": messages, "temperature": 0.7, "stream": True}
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
    url = f"{ALI_TARGET_URL}/v1/chat/completions"
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {ALI_API_KEY}'}
    messages = []
    if data.get('systemInstruction'): messages.append({"role": "system", "content": data.get('systemInstruction')})
    for item in data.get('history', []):
        if item.get('role') and item.get('parts'):
            messages.append({"role": item.get('role'), "content": item.get('parts')[0].get('text')})
    messages.append({"role": "user", "content": data.get('userPrompt')})
    payload = {"model": ALI_MODEL, "messages": messages, "temperature": 0.7}
    response = requests.post(url, headers=headers, json=payload, timeout=180)
    response.raise_for_status()
    # Ali returns a slightly different structure sometimes? Assuming standard OpenAI format for compat API
    return jsonify(response.json()['choices'][0]['message']['content'])

def stream_ali_proxy(user_prompt, system_instruction, history):
    url = f"{ALI_TARGET_URL}/v1/chat/completions"
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {ALI_API_KEY}'}
    messages = []
    if system_instruction: messages.append({"role": "system", "content": system_instruction})
    for item in history:
        if item.get('role') and item.get('parts'):
            messages.append({"role": item.get('role'), "content": item.get('parts')[0].get('text')})
    messages.append({"role": "user", "content": user_prompt})
    payload = {"model": ALI_MODEL, "messages": messages, "temperature": 0.7, "stream": True}
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
