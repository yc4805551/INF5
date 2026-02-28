import logging
import json
import re
import os
import traceback
from core.services import llm_engine, current_engine
from .prompts import SYSTEM_PROMPT_OLD_YANG, PLANNER_SYSTEM_PROMPT, REVIEWER_SYSTEM_PROMPT
from .tools import ToolRegistry

logger = logging.getLogger(__name__)

class AgentEngine:
    def __init__(self, service_context):
        self.context = service_context # SmartFillerService instance
        self.registry = ToolRegistry(service_context)
        self.max_steps = 10
        self.history = [] # List of messages

    def _log_debug(self, message):
        """Proxy to service's debug logger"""
        if hasattr(self.context, '_log_debug'):
            self.context._log_debug(message)
        else:
            logger.info(message)

    def run(self, instruction, model_config=None, plan=None):
        """
        Executes the Agent Loop.
        """
        self._log_debug(f"--- OLD YANG AGENT STARTED ---")
        self._log_debug(f"Instruction: {instruction}")

        # 1. Planning Phase (Pattern 3)
        plan_str = "No Plan"
        plan_json = []

        if plan:
            self._log_debug("Using User-Provided Plan")
            plan_json = plan
            plan_str = json.dumps(plan_json, indent=2, ensure_ascii=False)
        else:
            try:
                plan_json = self._generate_plan(instruction, model_config)
                plan_str = json.dumps(plan_json, indent=2, ensure_ascii=False)
                self._log_debug(f"Plan Generated: {plan_str}")
            except Exception as pe:
                self._log_debug(f"Planning Failed (Skipping): {pe}")

        # 2. 获取运行时上下文信息
        canvas_info = self._get_canvas_info()
        ref_docs_info = self._get_reference_docs_info()
        
        # 3. 构建增强的System Prompt
        context_injection = f"""
【运行时上下文】
{canvas_info}

{ref_docs_info}

⚠️ 重要提醒：
- 你的修改操作必须针对【当前画布文档】(通过 `doc` 变量访问)
- 参考文档仅供读取，不可修改
- 当用户说"修改"或"填入"时，是指把参考文档的信息填入画布文档
"""

        system_prompt_with_plan = f"{SYSTEM_PROMPT_OLD_YANG}\n\n{context_injection}\n\n[Current Plan]\n{plan_str}\n\nPlease execution the plan step by step."
        
        self.history = [
            {"role": "system", "content": system_prompt_with_plan},
            {"role": "user", "content": instruction}
        ]

        # 2. Config Resolution
        api_key, provider, model, endpoint = self._resolve_config(model_config)
        if not api_key and provider != "mock":
             self._log_debug("Error: No API Key found.")
             return {"status": "error", "message": "未检测到 API Key。请配置 .env.local。"}

        step_count = 0
        final_answer = None
        
        while step_count < self.max_steps:
            step_count += 1
            self._log_debug(f"\n--- Step {step_count} ---")

            # 3. Call LLM
            # 3. Call LLM
            if provider == "mock":
                response_text = self._mock_response(step_count)
            else:
                try:
                    # Construct prompt from history
                    # Simple concat for non-chat models or use specialized method if llm_engine supports it
                    full_prompt = self._serialize_history()
                    self._log_debug(f"Calling LLM ({model})...")
                    # CRITICAL FIX: Add stop token to prevent hallucinating Observation
                    response_text = llm_engine._call_openai_compatible(
                        api_key, endpoint, model, full_prompt, stop=["Observation:", "\nObservation:"]
                    )
                except Exception as e:
                    self._log_debug(f"LLM Error: {e}")
                    return {"status": "error", "message": f"LLM Call Failed: {e}"}

            self._log_debug(f"LLM Response: {response_text}")
            self.history.append({"role": "assistant", "content": response_text})

            # 4. Parse Response (Thought/Action/Final Answer)
            parsed = self._parse_output(response_text)
            
            if parsed['final_answer']:
                final_answer = parsed['final_answer']
                self._log_debug(f"Final Answer Reached: {final_answer}")
                
                # --- Reflection Logic ---
                self._log_debug("--- Triggering Reflection ---")
                try:
                    # Pass current config to reflection
                    reflection = self._reflect(instruction, plan_json, final_answer, (api_key, provider, model, endpoint))
                    self._log_debug(f"Reflection Result: {reflection}")
                    
                    if reflection.get('status') == 'pass':
                         return {
                            "status": "success",
                            "message": final_answer,
                            "critique": reflection.get('critique', 'Review Passed.'),
                            "trace": [msg['content'] for msg in self.history if msg['role'] != 'system']
                        }
                    else:
                        # Review Failed
                        critique = reflection.get('critique', 'Unknown issue')
                        suggestion = reflection.get('suggestion', 'Please fix based on critique.')
                        
                        self._log_debug(f"Review Failed: {critique}")
                        
                        # Apply Feedback to History
                        feedback_msg = f"Reviewer Critique: {critique}\nSuggestion: {suggestion}\nPlease fix the issue and output a new Action or Final Answer."
                        self.history.append({"role": "user", "content": feedback_msg})
                        
                        # Reset final_answer to allow loop to continue
                        final_answer = None 
                        # Loop continues...
                except Exception as re:
                     self._log_debug(f"Reflection Logic Failed: {re}")
                     # Fallback to success if review crashes
                     return {
                        "status": "success",
                        "message": final_answer,
                        "critique": "Review Logic Error (Bypassed)",
                        "trace": [msg['content'] for msg in self.history if msg['role'] != 'system']
                     }
            
            if parsed['action']:
                tool_name = parsed['action']
                tool_args = parsed['action_input']
                
                self._log_debug(f"Tool Call: {tool_name} with {tool_args}")
                
                tool_func = self.registry.get_tool(tool_name)
                if tool_func:
                    try:
                        # Parse JSON input if possible
                        # global json import is sufficient
                        kwargs = {}
                        kwargs = {}
                        if isinstance(tool_args, dict):
                            kwargs = tool_args
                        elif isinstance(tool_args, str) and tool_args.strip().startswith('{'):
                            try:
                                kwargs = json.loads(tool_args)
                            except:
                                kwargs = {"raw_input": tool_args} # Fallback
                        elif tool_args:
                             # Legacy string input support or single arg
                             kwargs = {"text": tool_args, "location": tool_args, "script_code": tool_args} 


                        if isinstance(kwargs, dict):
                             observation = tool_func(**kwargs)
                        else:
                             observation = tool_func(tool_args) # specific simple tools

                    except Exception as e:
                        observation = f"Tool Execution Error: {str(e)}"
                else:
                    observation = f"Error: Tool '{tool_name}' not found."
                
                self._log_debug(f"Observation: {observation}")
                
                # Append Observation to history
                self.history.append({"role": "user", "content": f"Observation: {observation}"})
            else:
                # No action, no final answer? Force loop to continue or stop if stuck
                self._log_debug("Warning: No Action or Final Answer parsed. Sending continue prompt.")
                self.history.append({"role": "user", "content": "请继续思考，输出 Action 或 Final Answer。"})
                
        # End of While Loop
        return {
            "status": "error",
            "message": "Agent execution exceeded max steps without Final Answer.",
            "trace": [msg['content'] for msg in self.history]
        }

    def _resolve_config(self, model_config):
        # Force reload .env.local to pick up changes without restart
        from dotenv import load_dotenv
        # current file: backend/features/smart_filler/agent_engine.py
        # root: ../../../..
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        dotenv_local = os.path.join(base_dir, 'config', '.env.local')
        if os.path.exists(dotenv_local):
            load_dotenv(dotenv_local, override=True)
            self._log_debug(f"Reloaded config from {dotenv_local}")
        else:
            self._log_debug(f"Config file not found at: {dotenv_local}")

        # Check raw env vars for debugging
        has_gemini = bool(os.getenv("GEMINI_API_KEY") or os.getenv("VITE_GEMINI_API_KEY"))
        has_openai = bool(os.getenv("OPENAI_API_KEY") or os.getenv("VITE_OPENAI_API_KEY"))
        has_deepseek = bool(os.getenv("DEEPSEEK_API_KEY") or os.getenv("VITE_DEEPSEEK_API_KEY"))
        self._log_debug(f"Env Check - Gemini: {has_gemini}, OpenAI: {has_openai}, DeepSeek: {has_deepseek}")

        if not model_config or not model_config.get("apiKey"):
             # Priority 1: Deepseek (Commonly used by user context)
             deepseek_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("VITE_DEEPSEEK_API_KEY")
             if deepseek_key:
                 provider = "deepseek"
                 api_key = deepseek_key
                 endpoint = os.getenv("DEEPSEEK_ENDPOINT") or os.getenv("VITE_DEEPSEEK_ENDPOINT")
                 model = os.getenv("DEEPSEEK_MODEL") or os.getenv("VITE_DEEPSEEK_MODEL") or "deepseek-chat"
                 
                 self._log_debug(f"Resolved Config -> Provider: {provider}, Model: {model}, Endpoint: {endpoint}")
                 self._log_debug(f"API Key (Masked): {api_key[:4]}...{api_key[-4:] if len(api_key)>8 else ''}")
                 return api_key, provider, model, endpoint

             # Priority 2: OpenAI
             openai_key = os.getenv("OPENAI_API_KEY") or os.getenv("VITE_OPENAI_API_KEY")
             if openai_key:
                 provider = "openai"
                 api_key = openai_key
                 endpoint = os.getenv("OPENAI_ENDPOINT") or os.getenv("VITE_OPENAI_ENDPOINT")
                 model = os.getenv("OPENAI_MODEL") or os.getenv("VITE_OPENAI_MODEL") or "gpt-3.5-turbo"
                 
                 self._log_debug(f"Resolved Config -> Provider: {provider}, Model: {model}, Endpoint: {endpoint}")
                 self._log_debug(f"API Key (Masked): {api_key[:4]}...{api_key[-4:] if len(api_key)>8 else ''}")
                 return api_key, provider, model, endpoint

             # Priority 3: Gemini
             gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("VITE_GEMINI_API_KEY")
             if gemini_key:
                 provider = "gemini"
                 api_key = gemini_key
                 endpoint = os.getenv("GEMINI_ENDPOINT") or os.getenv("VITE_GEMINI_ENDPOINT")
                 model = os.getenv("GEMINI_MODEL") or os.getenv("VITE_GEMINI_MODEL") or "gemini-2.5-flash"

                 self._log_debug(f"Resolved Config -> Provider: {provider}, Model: {model}, Endpoint: {endpoint}")
                 self._log_debug(f"API Key (Masked): {api_key[:4]}...{api_key[-4:] if len(api_key)>8 else ''}")
                 return api_key, provider, model, endpoint

             # Priority 4: AnythingLLM (New)
             anything_key = os.getenv("ANYTHING_LLM_API_KEY") # Optional if no auth
             anything_url = os.getenv("ANYTHING_LLM_API_BASE")
             if anything_url:
                 provider = "anything" # Treat as openai-compatible
                 model = "anything-llm" # Model name usually ignored by AnythingLLM proxy or set in workspace
                 endpoint = anything_url # e.g. http://localhost:3001/api/v1
                 
                 # Adjust endpoint for OpenAI compatible route if needed
                 # AnythingLLM exposes /openai/v1 typically for drop-in
                 if not endpoint.endswith("/openai/v1"):
                     # If user provided base /api/v1, we might need /openai/v1 for standard chat completions
                     # OR we use the agent_anything service for chat. 
                     # But AgentEngine uses llm_engine._call_openai_compatible which expects standardized OpenAI definition.
                     # AnythingLLM's developer API is /api/v1/workspace/...
                     # BUT it also offers an OpenAI compatible endpoint at /v1 (beta) or similar? 
                     # Actually, for "Chat with Workspace", it's a specific API.
                     # Let's fallback to "openai" provider logic IF the endpoint is compatible.
                     pass 

                 self._log_debug(f"Resolved Config -> Provider: {provider} (AnythingLLM), Model: {model}, Endpoint: {endpoint}")
                 return anything_key, provider, model, endpoint

             # Priority 5: No Key Found
             self._log_debug("Error: No API Key found in env vars.")
             return None, None, None, None
        
        return model_config.get("apiKey"), model_config.get("provider"), model_config.get("model"), model_config.get("endpoint")

    def _serialize_history(self):
        # Convert list of dicts to string for pure completion API
        # Or better: construct a prompt that includes the history
        # Since _call_openai_compatible takes (..., prompt), we merge history.
        # Format:
        # System: ...
        # User: ...
        # Assistant: ...
        # User (Observation): ...
        
        prompt = ""
        for msg in self.history:
            role = msg['role'].capitalize()
            content = msg['content']
            prompt += f"{role}: {content}\n\n"
        return prompt

    def generate_plan_only(self, instruction, model_config):
        """Public method to generate a plan without executing it."""
        return self._generate_plan(instruction, model_config)

    def _generate_plan(self, instruction, model_config):
        """Pattern 3: Planning Agent"""
        self._log_debug("--- Planning Phase ---")
        api_key, provider, model, endpoint = self._resolve_config(model_config)
        if not api_key and provider != "mock":
             return []
        
        # 1. Gather Context from Service
        self._log_debug(f"Planner Context Check: current_engine={current_engine}, doc={current_engine.doc if current_engine else 'None'}")
        
        doc_structure = "No document loaded."
        if current_engine.doc:
            try:
                doc_structure = current_engine.get_global_context() or "Document loaded, but no obvious structure found."
                self._log_debug(f"Planner Doc Structure Length: {len(doc_structure)}")
            except Exception as e:
                self._log_debug(f"Error getting doc structure: {e}")
                doc_structure = "Error reading document structure."
            
        source_summary = "No source data."
        if self.context.current_df is not None:
             cols = ", ".join(self.context.current_df.columns.tolist())
             source_summary = f"Excel Loaded. Columns: {cols}. Rows: {len(self.context.current_df)}"
        elif self.context.current_context_text:
             source_summary = f"Source Text Loaded. Length: {len(self.context.current_context_text)} chars."
        
        self._log_debug(f"Planner Source Summary: {source_summary}")

        # 2. Build Context-Aware Prompt
        user_input = f"""
用户指令: {instruction}

【文档结构】:
{doc_structure}

【可用数据源】:
{source_summary}
"""
        prompt = f"{PLANNER_SYSTEM_PROMPT}\n\n{user_input}"
        
        if provider == "mock":
            return [{"step": 1, "description": "Mock Step (Context Aware)", "tool_hint": "mock_tool"}]
            
        try:
            response = llm_engine._call_openai_compatible(api_key, endpoint, model, prompt)
            # Cleanup code blocks if any
            response = response.replace("```json", "").replace("```", "").strip()
            return json.loads(response)
        except Exception as e:
            logger.error(f"Planner Error: {e}")
            logger.error(f"Planner Error: {e}")
            raise e

    def _reflect(self, instruction, plan_json, final_answer, config=None):
        """Pattern 4: Reflection Agent (Reviewer)"""
        self._log_debug("--- Reflection Phase ---")
        
        if config:
            api_key, provider, model, endpoint = config
        else:
            # Fallback if not passed (should not happen in new loop)
            api_key, provider, model, endpoint = self._resolve_config(None) 
            
        if not api_key and provider != "mock":
             return {"status": "pass", "critique": "Skipped review (No Key)"}

        plan_str = json.dumps(plan_json, ensure_ascii=False)
        trace_str = self._serialize_history()
        
        prompt = f"""{REVIEWER_SYSTEM_PROMPT}

【用户指令】: {instruction}
【执行计划】: {plan_str}
【执行过程】: 
{trace_str}
【最终结果】: {final_answer}
"""
        if provider == "mock":
             return {"status": "pass", "critique": "Mock Pass"}

        try:
             response = llm_engine._call_openai_compatible(api_key, endpoint, model, prompt)
             response = response.replace("```json", "").replace("```", "").strip()
             return json.loads(response)
        except Exception as e:
             logger.error(f"Reflection Failed: {e}")
             return {"status": "pass", "critique": f"Reflection Error: {e}"} # Fail open safe

    def _construct_system_prompt(self):
        """
        Constructs the ReAct system prompt with dynamic tool definitions.
        """
        # Get standardized schema
        tool_definitions = self.tools.get_tools_schema()
        
        # Format for ReAct (JSON-like representation)
        tools_desc = []
        for tool in tool_definitions:
            schema_str = json.dumps(tool['input_schema'], ensure_ascii=False)
            tools_desc.append(f"- {tool['name']}: {tool['description']}\n  Arguments Schema: {schema_str}")
            
        tools_str = "\n".join(tools_desc)

        prompt = f"""你是一个智能填充助手（Smart Filler Agent），能够操作 Word 文档并分析数据。

【可用工具】:
{tools_str}

【格式说明】:
请使用以下格式来执行工具：

Thought: 思考下一步该做什么
Action: 要执行的操作，必须是 [{', '.join([t['name'] for t in tool_definitions])}] 中的一个
Action Input: 操作的输入参数，必须是符合“Arguments Schema”的有效 JSON 格式。
Observation: 操作的结果... (这部分将由系统提供)

... (重复 Thought/Action/Observation N 次)

当你完成任务时：
Final Answer: [你对用户的最终回答]

【约束条件】:
1. 在写入文档前，必须始终验证你是否已经获取了必要的数据（来自 Excel/Docx）。
2. 在填充表格时，如果不确定，尽量先找到“锚点”（表头）。
3. 如果使用 'execute_document_script'，请确保生成的 Python 代码安全且正确。
4. 如果你需要停止或者无法继续执行，请提供 Final Answer 并解释原因。
"""
        return prompt

    def _parse_output(self, text):
        """
        Parses ReAct format:
        Thought: ...
        Action: ...
        Action Input: ...
        OR
        Final Answer: ...
        """
        result = {"thought": None, "action": None, "action_input": {}, "final_answer": None}
        
        # Regex for Action
        action_match = re.search(r'Action:\s*(.+)', text)
        if action_match:
            result['action'] = action_match.group(1).strip()
            
        # Regex for Action Input
        # Allow for possible newlines or extra spaces between Input: and {
        # Regex for Action Input
        # IMPROVED: Capture everything until Observation or End, don't enforce constraints like {}
        input_match = re.search(r'Action Input:\s*(.*?)(?:\nObservation:|$)', text, re.DOTALL)
        if input_match:
            raw_input = input_match.group(1).strip()
            # Try to parse as JSON first
            try:
                # Naive cleanup: sometimes it wraps in ```json ... ```
                # We can strip it
                clean_json = raw_input.replace('```json', '').replace('```', '').strip()
                result['action_input'] = json.loads(clean_json)
            except:
                # If NOT JSON, pass as "raw_input" so tools can try to parse/use it
                logger.warning(f"Action Input is not valid JSON. Passing as raw_input. Content: {raw_input[:50]}...")
                result['action_input'] = {"raw_input": raw_input}
        
        # Regex for Final Answer
        final_match = re.search(r'Final Answer:\s*(.+)', text, re.DOTALL)
        if final_match:
            result['final_answer'] = final_match.group(1).strip()
            
        return result

    def _mock_response(self, step):
        # Simulated behavior for testing
        if step == 1:
            return 'Thought: 用户想填充数据。我需要先看 Excel。\nAction: read_excel_summary\nAction Input: {}'
        elif step == 2:
            return 'Thought: Excel 里有“招聘名额”列。用户没具体说填哪，我假设填入 Word 的表格。\nAction: find_anchor_in_word\nAction Input: {"text": "名额"}'
        else:
            return 'Subject: Mock Task\nFinal Answer: 模拟执行完成。请配置 API Key 以启用真 AI。'
    
    def _get_canvas_info(self):
        """
        获取当前画布文档的详细信息
        Returns:
            格式化的画布文档信息字符串
        """
        from core.services import current_engine
        
        if not current_engine.doc:
            return "【当前画布文档】\n- 状态: 未加载"
        
        doc = current_engine.doc
        para_count = len(doc.paragraphs)
        table_count = len(doc.tables)
        
        # 获取文档预览（前3个非空段落）
        preview_lines = []
        preview_count = 0
        for i, p in enumerate(doc.paragraphs):
            if p.text.strip() and preview_count < 3:
                text_preview = p.text[:60] + '...' if len(p.text) > 60 else p.text
                preview_lines.append(f"  第{i+1}段: {text_preview}")
                preview_count += 1
        
        # 获取文件名
        filename = getattr(current_engine, 'original_path', None)
        if filename:
            import os
            filename = os.path.basename(filename)
        else:
            filename = "(内存文档，未保存)"
        
        info = f"""【当前画布文档】（你的修改目标）
- 文件名: {filename}
- 段落总数: {para_count}
- 表格总数: {table_count}"""
        
        if preview_lines:
            info += "\n- 内容预览:\n" + "\n".join(preview_lines)
        
        return info
    
    def _get_reference_docs_info(self):
        """
        获取参考文档列表信息
        Returns:
            格式化的参考文档列表字符串
        """
        from core.services import current_engine
        
        if not current_engine.reference_docs:
            return "【参考文档】\n- 状态: 无参考文档加载"
        
        lines = ["【参考文档】（只读，仅供参考）"]
        for idx, ref in enumerate(current_engine.reference_docs, 1):
            filename = ref.get('filename', 'Unknown')
            ref_type = ref.get('type', 'unknown')
            
            # 额外信息
            extra_info = ""
            if ref_type == 'excel' and 'df' in ref:
                cols_count = len(ref['df'].columns)
                rows_count = len(ref['df'])
                extra_info = f" | {rows_count}行 x {cols_count}列"
            elif ref_type == 'docx' and 'doc' in ref:
                para_count = len(ref['doc'].paragraphs)
                extra_info = f" | {para_count}个段落"
            
            lines.append(f"{idx}. {filename} (类型: {ref_type}{extra_info})")
        
        lines.append("\n提示: 使用 read_source_content 工具可查看所有参考文档内容")
        
        return "\n".join(lines)
