# ... existing code ...
# --- 3. HELPER & DIAGNOSTIC FUNCTIONS ---
def get_available_ollama_models():
    try:
        if not ollama_client: 
            print("[ERROR] Ollama客户端未初始化")
            return []
        response = ollama_client.list()
        print(f"[DEBUG] Ollama list response: {response}")
        models_list = response.get('models', [])
        if not isinstance(models_list, list): 
            print(f"[ERROR] Ollama返回的models不是列表类型: {type(models_list)}")
            return []
        available_models = [model['name'] for model in models_list if isinstance(model, dict) and 'name' in model]
        print(f"[DEBUG] Available Ollama models: {available_models}")
        return available_models
    except Exception as e:
        print(f"[ERROR] 获取Ollama可用模型失败: {str(e)}")
        # 在调试模式下，可以返回一个模拟的模型列表以便测试
        # return ["qwen3-embedding:0.6b"]  # 仅用于调试
        return []

def find_full_ollama_model_name(short_name, available_models):
    """
    在可用模型列表中查找与 short_name 完全匹配的模型名称。
    Ollama API 返回的名称可能包含 "latest" 标签, 例如 "qwen3-embedding:0.6b" 或 "qwen3-embedding:0.6b:latest"。
    此函数会同时检查这两种可能性。
    """
    # 直接检查精确匹配，例如 "qwen3-embedding:0.6b"
    if short_name in available_models:
        return short_name
    
    # 检查是否带有 "latest" 标签，例如 "qwen3-embedding:0.6b:latest"
    name_with_latest_tag = f"{short_name}:latest"
    if name_with_latest_tag in available_models:
        return name_with_latest_tag
        
    # 如果两种情况都未找到，则返回 None
    return None

@app.route('/api/find-related', methods=['POST'])
def find_related():
    is_ok, msg = services_are_ok()
    if not is_ok: 
        print(f"[ERROR] 服务检查失败: {msg}")
        return jsonify({"error": msg}), 503
    data = request.get_json()
    text, coll_name, emb_model_short, top_k = data.get('text'), data.get('collection_name'), data.get('embedding_model'), data.get('top_k', 10)
    if not all([text, coll_name, emb_model_short]): 
        print(f"[ERROR] 缺少必要参数: text={text}, collection_name={coll_name}, embedding_model={emb_model_short}")
        return jsonify({"error": "缺少 text, collection_name, 或 embedding_model 参数"}), 400
    
    print(f"[DEBUG] 收到find-related请求: collection={coll_name}, model={emb_model_short}")
    available_models = get_available_ollama_models()
    emb_model_full = find_full_ollama_model_name(emb_model_short, available_models)
    if not emb_model_full: 
        print(f"[ERROR] 模型不可用: '{emb_model_short}'")
        return jsonify({"error": f