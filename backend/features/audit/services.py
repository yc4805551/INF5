import logging
import re
import base64
import os
import json
from typing import Dict, Any, List
from core.services import current_engine, llm_engine
from core.llm_config import get_llm_config_manager
from features.agent_anything import perform_anything_audit # Dual Engine Support

def perform_audit(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Orchestrates the audit process. 
    Aggregates Source Material (Reference Docs + Images) and Target Document,
    then triggers the LLM Audit.
    """
    # [Dual Engine Routing]
    if os.getenv("ENABLE_ANYTHING_AGENT", "True") == "True":
        logging.info("Dual Engine: Routing to AnythingLLM Agent...")
        rules = data.get("rules", "Check for consistency in dates, amounts, and names.")
        target_text = current_engine.get_all_content()
        source_text = current_engine.get_reference_context() or "(No source documents provided)"
        
        # Call Anything Service directly
        return perform_anything_audit(target_text, source_text, rules)

    rules = data.get("rules", "Check for consistency in dates, amounts, and names.")
    model_config = data.get("model_config", {}) or {}

    # --- Robust Key Resolution (Same as Advisor) ---
    def get_conf(key, env_var, default=None):
        val = model_config.get(key)
        if val and str(val).strip(): return val
        # Try VITE_ prefix first
        vite = os.getenv(f"VITE_{env_var}")
        if vite: return vite
        # Standard env
        norm = os.getenv(env_var)
        if norm: return norm
        return default

    # 1. Decide Provider
    provider = model_config.get("provider")
    if not provider:
        if os.getenv("VITE_DEEPSEEK_API_KEY") or os.getenv("DEEPSEEK_API_KEY"):
            provider = "deepseek"
        elif os.getenv("VITE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY"):
            provider = "openai"
        elif os.getenv("VITE_ALI_API_KEY") or os.getenv("ALI_API_KEY"):
            provider = "aliyun"
        else:
            provider = "gemini"
    
    # 2. Resolve Creds
    if provider == "deepseek":
        api_key = get_conf("apiKey", "DEEPSEEK_API_KEY")
        endpoint = get_conf("endpoint", "DEEPSEEK_BASE_URL")
        if not endpoint: endpoint = get_conf("endpoint", "DEEPSEEK_ENDPOINT", "https://api.deepseek.com/v1")
        model = get_conf("model", "DEEPSEEK_MODEL_NAME", "deepseek-chat")
    elif provider == "openai":
        api_key = get_conf("apiKey", "OPENAI_API_KEY")
        endpoint = get_conf("endpoint", "OPENAI_BASE_URL")
        if not endpoint: endpoint = get_conf("endpoint", "OPENAI_ENDPOINT", "https://api.openai.com/v1")
        model = get_conf("model", "OPENAI_MODEL_NAME", "gpt-3.5-turbo")
    else: # Gemini fallback
        provider = "gemini"
        api_key = get_conf("apiKey", "GOOGLE_API_KEY")
        if not api_key: api_key = get_conf("apiKey", "GEMINI_API_KEY") # Check Gemini variant
        endpoint = get_conf("endpoint", "GOOGLE_API_BASE", None)
        model = get_conf("model", "GOOGLE_MODEL_NAME", "gemini-2.0-flash-exp")

    # 3. Update model_config for LLM Engine
    model_config["provider"] = provider
    model_config["apiKey"] = api_key
    model_config["endpoint"] = endpoint
    model_config["model"] = model
    
    logging.info(f"Audit Service: Using Provider={provider} Model={model}")
    
    # 1. Get Target Text (Main Doc)
    target_text = current_engine.get_all_content()
    
    if not target_text:
        return {"error": "No target document loaded. Please upload a document to the Canvas first."}

    # 2. Get Source Text (References)
    # We use get_reference_context which returns Markdown (including image links)
    source_text = current_engine.get_reference_context()
    
    if not source_text:
        source_text = "(No source documents provided)"

    # 3. Collect Images from Source
    # Parse the Markdown in source_text to find local image paths
    # Matches: ![alt](/static/images/filename.png)
    images = []
    
    # Locate backend root for file resolution
    # path: backend/features/audit/services.py -> backend/
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    img_matches = re.findall(r'!\[.*?\]\((.*?)\)', source_text)
    
    for img_path in img_matches:
        # Filter for our static images
        if "/static/images/" in img_path:
            # Clean path to be relative to backend root
            # img_path might be "/static/images/..."
            try:
                # Remove leading slash if present to join correctly
                rel_path = img_path.lstrip("/") 
                abs_path = os.path.join(base_dir, *rel_path.split("/"))
                
                if os.path.exists(abs_path):
                    with open(abs_path, "rb") as img_f:
                        b64_data = base64.b64encode(img_f.read()).decode('utf-8')
                        
                        # Detect mime
                        mime = "image/png"
                        if abs_path.lower().endswith(".jpg") or abs_path.lower().endswith(".jpeg"): 
                            mime = "image/jpeg"
                        elif abs_path.lower().endswith(".webp"):
                             mime = "image/webp"

                        images.append(f"data:{mime};base64,{b64_data}")
                        logging.info(f"Audit: Included image {os.path.basename(abs_path)}")
            except Exception as e:
                logging.error(f"Audit: Failed to load image {img_path}: {e}")

import asyncio

async def perform_audit(data: Dict[str, Any]) -> Dict[str, Any]:
    # 1. Extract Data
    source_text = data.get("source", "")
    target_text = data.get("content", "")
    rules = "\n".join(data.get("rules", []))
    model_config = data.get("model_config", {}) or {}
    
    # 使用统一配置管理器（与perform_audit_stream保持一致）
    logging.info(f"[Audit] Original model_config: {model_config}")
    config_manager = get_llm_config_manager()
    model_config = config_manager.resolve_config(model_config)
    
    provider = model_config.get("provider", "openai")
    api_key = model_config.get("apiKey", "")
    endpoint = model_config.get("endpoint", "")
    model = model_config.get("model", "")
    
    logging.info(f"[Audit] Resolved Provider={provider}, Model={model}, Endpoint={endpoint}, HasAPIKey={bool(api_key)}")
    
    # 3. Collect Images from Source
    # Parse the Markdown in source_text to find local image paths
    # Matches: ![alt](/static/images/filename.png)
    images = []
    
    # Locate backend root for file resolution
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        img_matches = re.findall(r'!\[.*?\]\((.*?)\)', source_text)
        
        for img_path in img_matches:
            # Filter for our static images
            if "/static/images/" in img_path:
                try:
                    rel_path = img_path.lstrip("/") 
                    abs_path = os.path.join(base_dir, *rel_path.split("/"))
                    
                    if os.path.exists(abs_path):
                        with open(abs_path, "rb") as img_f:
                            b64_data = base64.b64encode(img_f.read()).decode('utf-8')
                            
                            # Detect mime
                            mime = "image/png"
                            if abs_path.lower().endswith(".jpg") or abs_path.lower().endswith(".jpeg"): 
                                mime = "image/jpeg"
                            elif abs_path.lower().endswith(".webp"):
                                mime = "image/webp"

                            images.append(f"data:{mime};base64,{b64_data}")
                            logging.info(f"Audit: Included image {os.path.basename(abs_path)}")
                except Exception as e:
                    logging.error(f"Audit: Failed to load image {img_path}: {e}")
    except Exception as e:
        # Fallback if path resolution fails
         logging.error(f"Audit: Failed to setup image paths: {e}")

    # 4. Call LLM (Agent Routing)
    logger = logging.getLogger(__name__)
    logger.info("Starting Audit Analysis...")

    from features.audit.agents import get_agent_prompt
    from features.audit.rule_engine import RuleEngine

    # Check if frontend requested specific agents
    requested_agents = data.get("agents", [])
    
    # Run Offline Rule Engine FIRST (Fast Check)
    rule_engine = RuleEngine()
    rule_issues = rule_engine.run_checks(target_text)
    
    # If no specific agents requested, fall back to the legacy "Audit All" single-prompt approach
    if not requested_agents or len(requested_agents) == 0:
        logger.info("No specific agents requested, using Legacy Monolithic Audit.")
        # Wrap legacy call in thread
        raw_result = await asyncio.to_thread(
            llm_engine.audit_document,
            source_text=source_text,
            target_text=target_text,
            rules=rules,
            images=images,  # images defined above in scope
            model_config=model_config
        )
        legacy_result = _parse_llm_result(raw_result)
        if "issues" in legacy_result:
            legacy_result["issues"] = rule_issues + legacy_result["issues"]
        else:
             legacy_result["issues"] = rule_issues
        return legacy_result

    # Multi-Agent Execution (Async Parallel)
    logger.info(f"Executing Specialized Agents (Async): {requested_agents}")
    
    async def _run_single_agent(agent_type):
        try:
            # Prepare optional rule context
            kwargs = {}
            if agent_type == "proofread":
                kwargs["user_typos"] = rule_engine.get_typos_text()
            elif agent_type == "terminology":
                kwargs["user_forbidden"] = rule_engine.get_forbidden_text()

            prompt = get_agent_prompt(agent_type, target_text, source_text, **kwargs)
            
            # Helper to run synchronous LLM call
            def _call_llm_sync():
                if provider == "gemini":
                    return llm_engine._call_google_gemini(api_key, prompt, endpoint, model, images)
                elif provider in ["openai", "deepseek", "aliyun"]:
                    return llm_engine._call_openai_compatible(api_key, endpoint, model, prompt)
                return "{}"
            
            agent_result_str = await asyncio.to_thread(_call_llm_sync)

            # Check for specific error prefixes from LLM Engine
            if agent_result_str.strip().startswith("# Error") or "403 Forbidden" in agent_result_str:
                logger.error(f"Agent {agent_type} returned error: {agent_result_str}")
                return [{
                    "type": "system_error",
                    "severity": "critical", 
                    "problematicText": "System Error",
                    "suggestion": "Check Backend Logs / API Key",
                    "reason": f"LLM Call Failed: {agent_result_str[:200]}"
                }]

            # Parse result
            parsed = _parse_llm_result(agent_result_str)
            if "issues" in parsed:
                # Tag issues with agent type
                for issue in parsed["issues"]:
                    issue["agent"] = agent_type
                return parsed["issues"]
            else:
                logger.warning(f"Agent {agent_type} returned no 'issues' key: {parsed}")
                # Return nothing (or low confidence warning) if truly empty
                return []
        except Exception as e:
            logger.error(f"Agent {agent_type} failed: {e}")
            return [{
                "type": "system_error",
                "severity": "critical",
                "problematicText": "Exception", 
                "suggestion": "Contact Support",
                "reason": str(e)
            }]
        return []

    # Launch all agents in parallel
    tasks = [_run_single_agent(agent) for agent in requested_agents]
    results_list = await asyncio.gather(*tasks)
    
    # Flatten results
    aggregated_issues = list(rule_issues)
    for res in results_list:
        aggregated_issues.extend(res)

    return {
        "status": "WARNING" if aggregated_issues else "PASS",
        "score": 100 - (len(aggregated_issues) * 5),
        "issues": aggregated_issues,
        "summary": f"Completed audit using async agents: {', '.join(requested_agents)}"
    }

def _parse_llm_result(raw_result: Any) -> Dict[str, Any]:
    try:
        if isinstance(raw_result, str):
            clean = raw_result.replace("```json", "").replace("```", "").strip()
            # Handle potential functional call formats or prefixes
            first_brace = clean.find("{")
            last_brace = clean.rfind("}")
            if first_brace != -1 and last_brace != -1:
                clean = clean[first_brace:last_brace+1]
                
            return json.loads(clean)
        return raw_result
    except Exception as e:
        return {"error": f"Failed to parse result: {e}", "raw_output": str(raw_result)}

def perform_audit_stream(data: Dict[str, Any]):
    """
    NDJSON流式审核：逐Issue返回，而非等待全部完成
    每行格式: {"type":"issue","data":{...}}\n
    使用统一配置管理器处理LLM配置。
    """
    # 1. Extract Data
    source_text = data.get("source", "")
    target_text = data.get("content", "")
    rules = "\n".join(data.get("rules", []))
    model_config = data.get("model_config", {}) or {}

    # 使用统一配置管理器
    logging.info(f"[Audit Stream] Original model_config: {model_config}")
    config_manager = get_llm_config_manager()
    model_config = config_manager.resolve_config(model_config)
    
    logging.info(f"[Audit Stream] Resolved Provider={model_config.get('provider')}, Model={model_config.get('model')}, Endpoint={model_config.get('endpoint')}, HasAPIKey={bool(model_config.get('apiKey'))}")

    # 2. Image Loading
    images = []
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        img_matches = re.findall(r'!\[.*?\]\((.*?)\)', source_text)
        for img_path in img_matches:
            if "/static/images/" in img_path:
                try:
                     rel_path = img_path.lstrip("/") 
                     abs_path = os.path.join(base_dir, *rel_path.split("/"))
                     if os.path.exists(abs_path):
                         with open(abs_path, "rb") as img_f:
                             b64_data = base64.b64encode(img_f.read()).decode('utf-8')
                             mime = "image/png"
                             if abs_path.lower().endswith((".jpg", ".jpeg")): mime = "image/jpeg"
                             elif abs_path.lower().endswith(".webp"): mime = "image/webp"
                             images.append(f"data:{mime};base64,{b64_data}")
                except: pass
    except: pass

    # 3. 【关键改变】：先完整获取LLM结果，再逐Issue包装为NDJSON
    try:
        # 调用非流式audit（完整返回JSON）
        full_result = llm_engine.audit_document(
            source_text=source_text,
            target_text=target_text,
            rules=rules,
            images=images,
            model_config=model_config
        )
        
        # 解析JSON
        if isinstance(full_result, str):
            import json
            try:
                full_result = json.loads(full_result)
            except:
                # 解析失败，返回错误
                yield json.dumps({"type": "error", "data": {"message": "Failed to parse LLM result"}}) + "\n"
                return
        
        # 逐Issue yield (NDJSON格式)
        issues = full_result.get("issues", [])
        for issue in issues:
            ndjson_line = json.dumps({"type": "issue", "data": issue}, ensure_ascii=False) + "\n"
            yield ndjson_line
        
        # 最后发送summary
        summary_data = {
            "status": full_result.get("status", "PASS"),
            "score": full_result.get("score", 100),
            "summary": full_result.get("summary", ""),
            "total_issues": len(issues)
        }
        yield json.dumps({"type": "summary", "data": summary_data}, ensure_ascii=False) + "\n"
    
    except Exception as e:
        logging.error(f"Audit stream error: {e}")
        yield json.dumps({"type": "error", "data": {"message": str(e)}}, ensure_ascii=False) + "\n"
