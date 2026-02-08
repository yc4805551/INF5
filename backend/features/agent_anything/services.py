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
    [Role]
    You are an expert document auditor.
    
    [Task]
    Audit the following document text based on the Knowledge Base you have access to.
    
    [Document Content]
    {target_text}
    
    [Specific Rules/Focus]
    {rules}
    
    [Instruction]
    1. Identify any discrepancies between the document and your Knowledge Base facts.
    2. Point out specific risks.
    3. Provide a structured review report.
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
        [Role]
        You are a Senior Editor ("Old Yang").
        
        [Input]
        Here is a draft audit report generated by a junior auditor:
        ---
        {draft_content}
        ---
        
        [Task]
        Critique and refine this report. 
        1. Remove hallucinations.
        2. Make the tone more professional.
        3. Output the FINAL report.
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
    [Instruction]
    You are a professional document writer. 
    Using the retrieved context from your knowledge base, write a comprehensive response to the following request.
    
    [User Request]
    {prompt}
    
    [Requirements]
    - Strict professional tone (Official Document style).
    - No conversational filler (e.g., "Here is the summary").
    - Use the facts from the knowledge base.
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
