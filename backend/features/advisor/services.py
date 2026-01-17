import logging
import json
import os
from core.services import llm_engine

logger = logging.getLogger(__name__)

class AdvisorService:
    def __init__(self):
        pass

    def generate_suggestions(self, selected_text: str, context_text: str, model_config: dict = None) -> list:
        """
        Orchestrates multiple agents (Proofreader, Polisher) to generate suggestions.
        """
        suggestions = []
        
        logger.info(f"AdvisorService: Starting generation... Text len: {len(selected_text)}")

        if not selected_text or len(selected_text.strip()) < 2:
            logger.info("AdvisorService: Text too short, skipping.")
            return []

        # 1. Proofreader Agent
        try:
            logger.info("AdvisorService: Running Proofreader...")
            proofread_res = self._run_proofreader(selected_text, context_text, model_config)
            if proofread_res:
                suggestions.append(proofread_res)
                logger.info("AdvisorService: Proofreader found issue.")
            else:
                logger.info("AdvisorService: Proofreader generated no output.")
        except Exception as e:
            logger.error(f"AdvisorService: Proofreader crashed: {e}")
            suggestions.append({
                "type": "error",
                "original": "System Error",
                "suggestion": "Check Backend Logs",
                "reason": f"Proofreader Agent Failed: {str(e)}"
            })

        # 2. Polisher Agent
        try:
            logger.info("AdvisorService: Running Polisher...")
            polish_res = self._run_polisher(selected_text, context_text, model_config)
            if polish_res:
                suggestions.append(polish_res)
                logger.info("AdvisorService: Polisher found improvement.")
            else:
                logger.info("AdvisorService: Polisher generated no output.")
        except Exception as e:
            logger.error(f"AdvisorService: Polisher crashed: {e}")
            suggestions.append({
                "type": "error",
                "original": "System Error",
                "suggestion": "Check Backend Logs",
                "reason": f"Polisher Agent Failed: {str(e)}"
            })
            
        logger.info(f"AdvisorService: Finished. Total suggestions: {len(suggestions)}")
        return suggestions

    def _run_proofreader(self, text, context, config):
        """
        Agent: Proofreader
        Goal: Find objective errors (typos, grammar).
        """
        prompt = f"""
        角色: 资深文案编辑
        任务: 检查以下文本是否存在拼写、语法或标点错误。
        上下文: ...{context[-200:] if context else ""}...
        
        待检查文本: "{text}"
        
        如果没有错误，直接输出: None
        如果存在错误，请输出 JSON:
        {{
            "type": "proofread",
            "original": "{text}",
            "suggestion": "修正后的文本",
            "reason": "简要解释错误原因（请务必使用中文）。"
        }}
        """
        return self._call_agent(prompt, config, "proofread")

    def _run_polisher(self, text, context, config):
        """
        Agent: Polisher
        Goal: Improve style, clarity, and professionalism.
        """
        prompt = f"""
        角色: 专业写作教练
        任务: 润色以下文本，使其更加简洁、专业、有力（公文风格）。
        上下文: ...{context[-200:] if context else ""}...
        
        待润色文本: "{text}"
        
        如果文本已经非常出色，无需修改，直接输出: None
        如有改进空间，输出 JSON:
        {{
            "type": "polish",
            "original": "{text}",
            "suggestion": "润色后的文本",
            "reason": "为什么这样改更好（例如'更简洁'、'用词更精准'，请使用中文）。"
        }}
        """
        return self._call_agent(prompt, config, "polish")

    def _call_agent(self, prompt, config, agent_type):
        MAX_RETRIES = 1
        
        # Helper to get config with fallback (including VITE_ prefix)
        def get_conf(key, env_var, default=None):
            # 1. Try explicit config from frontend argument
            val = config.get(key)
            if val and str(val).strip(): return val

            # 2. Try VITE_ prefixed env var (Priority)
            vite_env_val = os.getenv(f"VITE_{env_var}")
            if vite_env_val: return vite_env_val

            # 3. Try standard env var
            env_val = os.getenv(env_var)
            if env_val: return env_val
            
            return default

        # Logic to execute the call
        def execute_call(provider, api_key, endpoint, model):
            if not api_key:
                 logger.warning(f"No API Key for {provider}")
                 return None, f"Missing API Key for provider: {provider}. Please check .env.local for {provider.upper()}_API_KEY or VITE_{provider.upper()}_API_KEY."
            
            # Log
            secure_key = (str(api_key)[:6] + "...")
            logger.info(f"Advisor Attempt: Provider={provider} | Endpoint={endpoint} | Model={model} | Key={secure_key}")

            res_text = ""
            try:
                if provider == "gemini":
                     if endpoint and ("/chat/completions" in endpoint or "/v1" in endpoint) and "googleapis.com" not in endpoint:
                          res_text = llm_engine._call_openai_compatible(api_key, endpoint, model, prompt)
                     else:
                          res_text = llm_engine._call_google_gemini(api_key, prompt, endpoint, model)
                else:
                     res_text = llm_engine._call_openai_compatible(api_key, endpoint, model, prompt)
            except Exception as call_err:
                return None, f"LLM Inference Error: {str(call_err)}"
            
            return res_text, None

        # --- Main Execution ---
        
        # Decide provider
        # Priority: 
        # 1. Frontend explicit config
        # 2. Env var DEFAULT_AI_PROVIDER
        # 3. Auto-detect based on available keys
        # 4. Fallback to Gemini
        
        provider = config.get("provider")
        if not provider:
            # Auto-detect
            if os.getenv("VITE_DEEPSEEK_API_KEY") or os.getenv("DEEPSEEK_API_KEY"):
                provider = "deepseek"
            elif os.getenv("VITE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY"):
                provider = "openai"
            elif os.getenv("VITE_ALI_API_KEY") or os.getenv("ALI_API_KEY"):
                provider = "aliyun" # Assuming logic handles this, though not in original if/else block yet
            else:
                provider = "gemini"
        
        logger.info(f"AdvisorService: Using AI Provider: {provider}")

        # Resolve creds based ONLY on that provider
        api_key = None
        endpoint = None
        model = None

        if provider == "gemini":
            # Try multiple variants for Gemini Key
            api_key = get_conf("apiKey", "GOOGLE_API_KEY") 
            if not api_key: api_key = get_conf("apiKey", "GEMINI_API_KEY") 
            
            endpoint = get_conf("endpoint", "GOOGLE_API_BASE", None) 
            model = get_conf("model", "GOOGLE_MODEL_NAME", "gemini-2.0-flash-exp")
        elif provider == "deepseek":
            api_key = get_conf("apiKey", "DEEPSEEK_API_KEY")
            endpoint = get_conf("endpoint", "DEEPSEEK_BASE_URL")
            if not endpoint:
                  endpoint = get_conf("endpoint", "DEEPSEEK_ENDPOINT", "https://api.deepseek.com/v1")
            model = get_conf("model", "DEEPSEEK_MODEL_NAME", "deepseek-chat")
        else:
            # OpenAI / Generic (User explicit preference)
            provider = "openai" 
            api_key = get_conf("apiKey", "OPENAI_API_KEY")
            endpoint = get_conf("endpoint", "OPENAI_BASE_URL")
            if not endpoint:
                    endpoint = get_conf("endpoint", "OPENAI_ENDPOINT")
            
            # Fallback only if absolutely no endpoint found
            if not endpoint: endpoint = "https://api.openai.com/v1"

            model = get_conf("model", "OPENAI_MODEL_NAME", "gpt-3.5-turbo")

        
        try:
            response_text, err = execute_call(provider, api_key, endpoint, model)
            
            if err:
                 logger.error(f"Agent Call Error: {err}")
                 # Return a mock error response to surface it
                 return {"type": "error", "original": "Config Error", "suggestion": "Fix Config", "reason": err}

            if not response_text or "Error" in response_text:
                logger.error(f"Agent Call Failed: {response_text or err}")
                return {"type": "error", "original": "LLM Error", "suggestion": "Retry", "reason": f"LLM returned error/empty: {response_text}"}
            
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                import re
                match = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
                if match: cleaned = match.group(1).strip()
            
            return json.loads(cleaned)
        
        except Exception as e:
            logger.error(f"Agent Exception: {e}")
            return None

advisor_service = AdvisorService()
