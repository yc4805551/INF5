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

        # --- Multi-Agent Collaboration ---
        
        # 1. Parallel Execution: Proofreader & Polisher
        # (In a real async system these would be parallel, here sequential for simplicity)
        
        raw_suggestions = []
        
        try:
            logger.info("AdvisorService: Running Proofreader...")
            proofread_res = self._run_proofreader(selected_text, context_text, model_config)
            if proofread_res: raw_suggestions.extend(proofread_res) # Use extend to flatten
        except Exception as e:
            logger.error(f"Proofreader Error: {e}")

        try:
            logger.info("AdvisorService: Running Polisher...")
            # Only run polisher if text is long enough to warrant style check
            if len(selected_text) > 5:
                polish_res = self._run_polisher(selected_text, context_text, model_config)
                if polish_res: raw_suggestions.extend(polish_res) # Use extend to flatten
        except Exception as e:
            logger.error(f"Polisher Error: {e}")

        if not raw_suggestions:
            return []
            
        # Deduplicate raw_suggestions before supervisor
        # Key: (original, suggestion)
        unique_raw = {}
        for s in raw_suggestions:
            key = (s.get('original'), s.get('suggestion'))
            if key not in unique_raw:
                unique_raw[key] = s
        raw_suggestions = list(unique_raw.values())

        # 2. Supervisor Agent (Aggregation & Self-Review)
        try:
            logger.info("AdvisorService: Running Supervisor (Self-Review)...")
            final_suggestions = self._run_supervisor(selected_text, raw_suggestions, context_text, model_config)
            
            # Double check deduplication on final result
            unique_final = {}
            for s in final_suggestions:
                key = (s.get('original'), s.get('suggestion'))
                if key not in unique_final:
                    unique_final[key] = s
            return list(unique_final.values())
            
        except Exception as e:
            logger.error(f"Supervisor Error: {e}")
            # Fallback: return raw suggestions if supervisor fails
            return raw_suggestions
            
    def _run_supervisor(self, original_text, suggestions_list, context, config):
        """
        Agent: Supervisor & Self-Review
        Goal: 
        1. Deduplicate suggestions.
        2. Resolve conflicts (e.g. Proofreader vs Polisher).
        3. SELF-REVIEW: Filter out bad suggestions (e.g. false positive numbers).
        """
        custom_rules = self._load_custom_rules()
        
        # Convert list to JSON string for the prompt
        suggestions_json = json.dumps(suggestions_list, ensure_ascii=False, indent=2)
        
        prompt = f"""
        你是一位【高级主编】。你的下属（校对员、润色师）对一段文本提出了一些修改建议。
        你的任务是：审查这些建议，去伪存真，输出最终的决策结果。

        【原文】
        "{original_text}"

        【下属提交的建议建议列表】
        {suggestions_json}

        【本地知识库 / 自定义规则】
        {custom_rules}

        【审查标准 (Self-Review Guidelines)】
        1.  **致命错误拦截 (Critical)**：
            -   **数字误判**：如果建议修改了 "2025年"、"第1名"、"增长5%" 等正常数字，**必须直接删除该建议**。
            -   **幻觉检测**：如果建议的修改让句子意思完全变了，或者改错了，删除它。
        2.  **去重与冲突解决**：
            -   如果两条建议针对同一个词，**优先保留 "Proofread" (纠错) 类型的建议**（因为硬伤必须改）。
            -   除非自定义规则明确指定了其他写法。
        3.  **最终输出**：
            -   只保留真正有价值、正确的建议。
            -   如果所有建议都被你驳回了，输出一个空数组 `[]`。

        【输出格式】
        请输出最终采纳的建议列表 JSON（格式与输入一致）：
        [
            {{ "type": "...", "original": "...", "suggestion": "...", "reason": "..." }},
            ...
        ]
        """
        
        try:
            # Re-use _call_agent logic but expect a list
            # We pass a dummy agent_type or handling in _call_agent? 
            # flexible _call_agent needed.
            res = self._call_agent(prompt, config, "supervisor")
            
            # Helper to ensure we get a list
            if isinstance(res, dict): return [res]
            if isinstance(res, list): return res
            return []
        except Exception as e:
            logger.error(f"Supervisor Parse Error: {e}")
            return suggestions_list # Fallback


    def _load_custom_rules(self) -> str:
        """
        Load custom correction rules from text file.
        """
        try:
            # Construct path relative to this file
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            file_path = os.path.join(base_dir, "audit", "data", "常见错误修改.txt")
            
            if not os.path.exists(file_path):
                return ""
                
            rules = []
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        rules.append(line)
            return "\n".join(rules)
        except Exception as e:
            logger.warning(f"Failed to load custom rules: {e}")
            return ""

    # --- Specialized Agents ---

    def _run_proofreader(self, text, context, config):
        """
        Proofreading Agent (Now powered by RealtimeAgent with Reflection).
        """
        try:
            # Delegate to independent RealtimeAgent
            from .realtime_agent import realtime_agent
            return realtime_agent.analyze_sentence(text, model_config=config)
        except Exception as e:
            logger.error(f"RealtimeAgent Delegation Error: {e}")
            return []

    def _run_polisher(self, text, context, config):
        """
        Agent: Polisher (Chinese Optimized)
        Goal: Improve style, clarity, and professionalism.
        """
        prompt = f"""
        你是一位资深的公文写作顾问。你的任务是润色以下文本，使其更具专业性、逻辑性和可读性。
        
        【上下文环境】
        ...{context[-300:] if context else ""}...
        
        【待润色文本】
        "{text}"
        
        【润色原则】
        1. **信达雅**：保持原意不变，提升表达的准确性和流畅度。
        2. **公文风格**：用词简练、正式，避免口语化（如把"搞定了"改为"已完成"）。
        3. **适度优化**：如果原文已经写得很好，请不要为了改而改，输出 None 即可。

        【输出格式】
        如果无需修改，直接输出: None
        如有改进建议，输出 JSON 格式（不要Markdown代码块，直接JSON）：
        {{
            "type": "polish",
            "original": "{text}",
            "suggestion": "润色后的完整文本",
            "reason": "用中文解释润色理由（如：‘用词更正式’、‘句式更通顺’）"
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
            # Model config for LLMEngine
            model_config = {
                "provider": provider,
                "apiKey": api_key,
                "endpoint": endpoint,
                "model": model
            }
            
            try:
                # Use unified generate method
                res_text = llm_engine.generate(prompt, model_config=model_config)
                
                # Check for error outputs from generate
                if res_text.startswith("# Error"):
                     # Standardize error
                     err_msg = res_text
                     if "429" in res_text or "Rate Limit" in res_text:
                         return None, "RATE_LIMIT_EXCEEDED"
                     return None, f"LLMEngine Error: {err_msg}"
                     
                return res_text, None

            except Exception as call_err:
                err_msg = str(call_err)
                logger.error(f"LLM Call Exception: {err_msg}")
                return None, f"Exception: {err_msg}"

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
                 if err == "RATE_LIMIT_EXCEEDED":
                     return None # Silent fail
                 
                 logger.error(f"Agent Call Error: {err}")
                 # Return a mock error response to surface it
                 return {"type": "error", "original": "Config Error", "suggestion": "Fix Config", "reason": err}

            if not response_text or response_text.strip().startswith("# Error"):
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
