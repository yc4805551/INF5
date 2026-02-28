import requests
import os
import logging
import json

# Configuration
ANYTHING_API_BASE = os.getenv("ANYTHING_LLM_API_BASE", "http://localhost:3001/api/v1")
ANYTHING_API_KEY = os.getenv("ANYTHING_LLM_API_KEY", "")

# Default Workspace (User should have created this)
# Default Workspace (User should have created this)
DEFAULT_WORKSPACE = os.getenv("ANYTHING_LLM_WORKSPACE", "inf_work")

def get_headers():
    key = ANYTHING_API_KEY
    if not key:
        logging.error("⚠️ AnythingLLM API Key is MISSING or EMPTY!")
    else:
        # Log first 4 chars for verification
        logging.info(f"Using anythingLLM API Key: {key[:4]}*** (Length: {len(key)})")
        
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

def get_anything_workspaces():
    """List all workspaces to find the valid slug"""
    url = f"{ANYTHING_API_BASE}/workspaces"
    try:
        response = requests.get(url, headers=get_headers(), timeout=10)
        response.raise_for_status()
        return response.json().get('workspaces', [])
    except Exception as e:
        logging.error(f"AnythingLLM WS List Failed: {e}")
        return []

def resolve_workspace_slug(target_name=DEFAULT_WORKSPACE):
    """Find the slug for the target workspace name"""
    workspaces = get_anything_workspaces()
    
    if not workspaces:
        logging.warning("No workspaces found in AnythingLLM")
        return None
    
    # Log all available workspaces for debugging
    logging.info(f"[Workspace Resolution] Looking for: '{target_name}'")
    logging.info(f"[Workspace Resolution] Available workspaces:")
    for ws in workspaces:
        ws_name = ws.get('name', 'N/A')
        ws_slug = ws.get('slug', 'N/A')
        logging.info(f"  - Name: '{ws_name}', Slug: '{ws_slug}'")
    
    # Try to match by name (case-insensitive)
    for ws in workspaces:
        ws_name = ws.get('name', '')
        ws_slug = ws.get('slug', '')
        
        # Match against name or slug
        if ws_name.lower() == target_name.lower() or ws_slug.lower() == target_name.lower():
            logging.info(f"[Workspace Resolution] ✓ Matched workspace: '{ws_name}' (slug: '{ws_slug}')")
            return ws_slug
    
    # No match found
    logging.warning(f"[Workspace Resolution] ✗ No workspace matching '{target_name}'")
    logging.warning(f"[Workspace Resolution] Defaulting to first workspace if available")
    
    # Fallback: return the first one if found
    if workspaces:
        fallback_ws = workspaces[0]
        fallback_name = fallback_ws.get('name', 'N/A')
        fallback_slug = fallback_ws.get('slug', 'N/A')
        logging.warning(f"[Workspace Resolution] Using fallback: '{fallback_name}' (slug: '{fallback_slug}')")
        return fallback_slug
    
    return None

def chat_with_anything(message, history=[], workspace_slug=None):
    """
    Send chat to AnythingLLM workspace.
    If workspace_slug is provided, use it directly; otherwise resolve from DEFAULT_WORKSPACE.
    Returns: { 'response': str, 'sources': list }
    """
    if not workspace_slug:
        slug = resolve_workspace_slug()
        if not slug:
            raise ValueError(f"No workspace found matching '{DEFAULT_WORKSPACE}' or system is empty.")
    else:
        slug = workspace_slug
        
    url = f"{ANYTHING_API_BASE}/workspace/{slug}/chat"
    
    # Specifically for Audit, we might want to inject context differently,
    # but for standard chat, AnythingLLM manages context via the Workspace vector DB.
    payload = {
        "message": message,
        "mode": "chat",
        "stream": True # Use streaming for stability
    }
    
    try:
        response = requests.post(url, headers=get_headers(), json=payload, stream=True, timeout=300)
        response.raise_for_status()
        
        full_response_text = []
        sources = []
        
        # Consuming the stream
        for line in response.iter_lines():
            if line:
                try:
                    decoded_line = line.decode('utf-8')
                    # Parse JSON chunk
                    chunk = json.loads(decoded_line)
                    
                    # Accumulate text
                    if 'textResponse' in chunk:
                        full_response_text.append(chunk['textResponse'])
                        
                    # Capture sources from the final chunk usually, or any chunk
                    if 'sources' in chunk and chunk['sources']:
                        sources = chunk['sources']
                        
                except Exception as parse_error:
                    logging.warning(f"Error parsing chunk: {parse_error}")
                    continue

        final_text = "".join(full_response_text)
        
        return {
            'response': final_text if final_text else 'No content received.',
            'sources': sources
        }
        
    except Exception as e:
        logging.error(f"AnythingLLM Chat Failed: {e}")
        raise e

def perform_anything_audit(target_text, source_context, rules):
    """
    Executes Audit using AnythingLLM RAG.
    We simulate the Agentic flow by sending prompt chains.
    """
    slug = resolve_workspace_slug()
    if not slug:
         return {
            "status": "ERROR", 
            "message": f"Please create a workspace named '{DEFAULT_WORKSPACE}' in AnythingLLM first."
        }

    # 1. Draft Phase
    # We construct a massive prompt because we can't easily 'upload' the raw text to vector db 
    # for just this single request without polluting the repo.
    # So we treat the Audit Target as "Context in Prompt" and ask AnythingLLM to query its Knowledge Base for "Norms".
    
    draft_prompt = f"""
    [角色扮演]
    你是一位专业的公文审核专家。
    
    [任务目标]
    请根据你能够访问的知识库，对以下文档内容进行审核。
    
    [文档内容]
    {target_text}
    
    [特定审核规则/关注重点]
    {rules}
    
    [执行指令]
    1. 识别并指出该文档与你知识库中所掌握的事实有任何不一致的地方。
    2. 明确指出文档中存在的具体风险点。
    3. 提供一份结构化的审核反馈报告。
    """

    url = f"{ANYTHING_API_BASE}/workspace/{slug}/chat"
    
    # Step 1: Draft
    try:
        resp_draft = requests.post(url, headers=get_headers(), json={"message": draft_prompt, "mode": "chat"}, timeout=120)
        resp_draft.raise_for_status()
        draft_content = resp_draft.json().get('textResponse', '')
        
        # Step 2: Critique (Simulated Reflection)
        # We send a follow-up message in the same conversation (if session is maintained? AnythingLLM is stateless unless sessionId provided, but here single turn might be safer or we construct new prompt)
        # For simplicity/robustness, we make a second discrete call with the previous context included in prompt if needed, 
        # OR we just accept the Draft for MVP v1.
        
        # Let's do a Critique call for high quality
        critique_prompt = f"""
        [角色扮演]
        你是资深总编（“老杨”）。
        
        [输入内容]
        以下是一份由初级审核员生成的初步审核报告草稿：
        ---
        {draft_content}
        ---
        
        [任务目标]
        请对该报告进行评判并润色完善。
        1. 剔除大模型的过度解读（幻觉）。
        2. 使审阅语气变得更加专业、严谨。
        3. 输出最终版本的审核报告。
        """
        
        resp_critique = requests.post(url, headers=get_headers(), json={"message": critique_prompt, "mode": "chat"}, timeout=120)
        resp_critique.raise_for_status()
        critique_content = resp_critique.json().get('textResponse', '')
        
        return {
            "status": "SUCCESS",
            "draft": draft_content,
            "critique": critique_content,
            "engine": "AnythingLLM"
        }

    except Exception as e:
        logging.error(f"Audit Chain Failed: {e}")
        return {"status": "ERROR", "message": f"AnythingLLM Error: {str(e)}"}

def generate_content_with_knowledge(prompt):
    """
    Generates content using AnythingLLM's RAG capabilities.
    """
    slug = resolve_workspace_slug()
    if not slug:
        return {
            "content": "Error: Knowledge Base workspace not found.",
            "sources": []
        }

    # Construct a strong instruction prompt
    # Since AnythingLLM handles retrieval, we just need to tell it HOW to write.
    full_message = f"""
    [执行指令]
    你是一名专业的公文执笔人。
    请利用你的知识库中检索到的上下文信息，对以下请求撰写一份全面且专业的回复。
    
    [用户请求]
    {prompt}
    
    [要求]
    - 严格保持专业的公文语气（党政机关公文风格）。
    - 不要使用任何对话式的客套话（例如：“好的，这里是总结”、“这份文件指出”等）。
    - 请基于且仅基于知识库中的事实进行陈述。
    """

    try:
        result = chat_with_anything(full_message, workspace_slug=slug)
        return {
            "content": result['response'],
            "sources": result['sources']
        }
    except Exception as e:
        return {
            "content": f"Error generating content: {str(e)}",
            "sources": []
        }
