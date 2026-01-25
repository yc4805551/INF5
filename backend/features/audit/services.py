import logging
import re
import base64
import os
import json
import asyncio
from typing import Dict, Any, List

# Core Services
from core.services import current_engine, llm_engine
from core.llm_config import get_llm_config_manager

# Feature Modules
from features.agent_anything import perform_anything_audit # Dual Engine Support
from features.audit.agents import get_agent_prompt
from features.audit.rule_engine import RuleEngine

logger = logging.getLogger(__name__)

async def perform_audit(data: Dict[str, Any]) -> Dict[str, Any]:
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

    # 1. Extract Data
    rules = data.get("rules", "Check for consistency in dates, amounts, and names.")
    model_config = data.get("model_config", {}) or {}
    requested_agents = data.get("agents", [])

    # 2. Resolve Config (Unified Manager)
    config_manager = get_llm_config_manager()
    resolved_config = config_manager.resolve_config(model_config)
    
    provider = resolved_config.get("provider", "openai")
    api_key = resolved_config.get("apiKey", "")
    endpoint = resolved_config.get("endpoint", "")
    model = resolved_config.get("model", "")
    
    logging.info(f"Audit Service: Using Provider={provider} Model={model}")

    # 3. Get Content
    target_text = current_engine.get_all_content()
    if not target_text:
        return {"error": "No target document loaded. Please upload a document to the Canvas first."}

    source_text = current_engine.get_reference_context()
    if not source_text:
        source_text = "(No source documents provided)"

    # 4. Collect Images
    images = _collect_images(source_text)

    # 5. Offline Rule Check (Fast)
    rule_engine = RuleEngine()
    rule_issues = rule_engine.run_checks(target_text)

    # 6. LLM Execution
    # If no specific agents requested, fall back to the legacy "Audit All" single-prompt approach
    if not requested_agents or len(requested_agents) == 0:
        logger.info("No specific agents requested, using Legacy Monolithic Audit.")
        raw_result = await asyncio.to_thread(
            llm_engine.audit_document,
            source_text=source_text,
            target_text=target_text,
            rules=rules,
            images=images,
            model_config=resolved_config
        )
        legacy_result = _parse_llm_result(raw_result)
        if "issues" in legacy_result:
            legacy_result["issues"] = rule_issues + legacy_result["issues"]
        else:
             legacy_result["issues"] = rule_issues
        return legacy_result

    # 7. Multi-Agent Execution (Async Parallel)
    logger.info(f"Executing Specialized Agents (Async): {requested_agents}")
    
    semaphore = asyncio.Semaphore(1 if provider == "gemini" else 5)

    async def _run_single_agent(agent_type):
        async with semaphore:
            try:
                # Prepare optional context
                kwargs = {}
                if agent_type == "proofread":
                    kwargs["user_typos"] = rule_engine.get_typos_text()
                elif agent_type == "terminology":
                    kwargs["user_forbidden"] = rule_engine.get_forbidden_text()

                prompt = get_agent_prompt(agent_type, target_text, source_text, **kwargs)
                
                # Sync LLM call wrapper
                def _call():
                    if provider == "gemini":
                        return llm_engine._call_google_gemini(api_key, prompt, endpoint, model, images)
                    elif provider in ["openai", "deepseek", "aliyun", "free"]:
                        return llm_engine._call_openai_compatible(api_key, endpoint, model, prompt)
                    return "{}"
                
                agent_result_str = await asyncio.to_thread(_call)
                
                # Error Check
                if agent_result_str.strip().startswith("# Error") or "403" in agent_result_str:
                    logger.error(f"Agent {agent_type} error: {agent_result_str}")
                    return []

                parsed = _parse_llm_result(agent_result_str)
                if isinstance(parsed, dict) and "issues" in parsed:
                    for issue in parsed["issues"]:
                        issue["agent"] = agent_type
                    return parsed["issues"]
                return []
            except Exception as e:
                logger.error(f"Agent {agent_type} exception: {e}")
                return []

    tasks = [_run_single_agent(agent) for agent in requested_agents]
    results_list = await asyncio.gather(*tasks)
    
    # Aggregate
    aggregated_issues = list(rule_issues)
    for res in results_list:
        aggregated_issues.extend(res)

    return {
        "status": "WARNING" if aggregated_issues else "PASS",
        "score": max(0, 100 - (len(aggregated_issues) * 5)),
        "issues": aggregated_issues,
        "summary": f"Completed audit using async agents: {', '.join(requested_agents)}"
    }

def perform_audit_stream(data: Dict[str, Any]):
    """
    NDJSON Stream Audit
    """
    # 1. Extract & Config
    source_text = data.get("source", "")
    target_text = data.get("content", "")
    rules = "\n".join(data.get("rules", []))
    model_config = data.get("model_config", {}) or {}

    config_manager = get_llm_config_manager()
    resolved_config = config_manager.resolve_config(model_config)
    
    # 2. Images
    images = _collect_images(source_text)

    # 3. Execution (Legacy Monolithic Style for Stream currently)
    try:
        full_result = llm_engine.audit_document(
            source_text=source_text,
            target_text=target_text,
            rules=rules,
            images=images,
            model_config=resolved_config
        )
        
        parsed = _parse_llm_result(full_result)
        
        # Yield Issues
        issues = parsed.get("issues", [])
        for issue in issues:
            yield json.dumps({"type": "issue", "data": issue}, ensure_ascii=False) + "\n"
        
        # Yield Summary
        summary_data = {
            "status": parsed.get("status", "PASS"),
            "score": parsed.get("score", 100),
            "summary": parsed.get("summary", ""),
            "total_issues": len(issues)
        }
        yield json.dumps({"type": "summary", "data": summary_data}, ensure_ascii=False) + "\n"
    
    except Exception as e:
        logging.error(f"Audit stream error: {e}")
        yield json.dumps({"type": "error", "data": {"message": str(e)}}, ensure_ascii=False) + "\n"

async def perform_realtime_check(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lightweight Realtime Check for Editor
    """
    # 1. Extract
    target_text = data.get("content", "")
    source_text = data.get("source", "")
    model_config = data.get("model_config", {})
    
    if not target_text or len(target_text) < 2:
        return {"issues": []}

    # 2. Offline Rules
    rule_engine = RuleEngine()
    rule_issues = rule_engine.run_checks(target_text)
    
    # 3. LLM (Proofread Only)
    config_manager = get_llm_config_manager()
    resolved_config = config_manager.resolve_config(model_config)
    
    provider = resolved_config.get("provider", "openai")
    api_key = resolved_config.get("apiKey", "")
    endpoint = resolved_config.get("endpoint", "")
    model = resolved_config.get("model", "")
    
    # Prompt
    user_typos = rule_engine.get_typos_text()
    prompt = get_agent_prompt("proofread", target_text, source_text, user_typos=user_typos)
    
    def _call_sync():
        if provider == "gemini":
            return llm_engine._call_google_gemini(api_key, prompt, endpoint, model, [])
        elif provider in ["openai", "deepseek", "aliyun", "free"]:
             return llm_engine._call_openai_compatible(api_key, endpoint, model, prompt)
        return "{}"

    try:
        raw_result = await asyncio.to_thread(_call_sync)
        parsed = _parse_llm_result(raw_result)
        ai_issues = parsed.get("issues", []) if isinstance(parsed, dict) else []
        return {"issues": rule_issues + ai_issues, "status": "PASS"}
    except Exception as e:
        logging.error(f"[Realtime] Failed: {e}")
        return {"issues": rule_issues}

# --- Helpers ---

def _collect_images(source_text: str) -> List[str]:
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
    return images

def _parse_llm_result(raw_result: Any) -> Dict[str, Any]:
    try:
        if isinstance(raw_result, str):
            clean = raw_result.replace("```json", "").replace("```", "").strip()
            first_brace = clean.find("{")
            last_brace = clean.rfind("}")
            if first_brace != -1 and last_brace != -1:
                clean = clean[first_brace:last_brace+1]
            return json.loads(clean)
        return raw_result
    except Exception:
        return {"error": "Failed to parse result", "raw": str(raw_result)}
