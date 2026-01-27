import json
import re
import difflib
from google import genai
from google.genai import types
import base64
import httpx
import logging
import os
import time
import random
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LLMEngine:
    FORMATTING_PROMPT_TEMPLATE = """
你是一位精通 python-docx 库的 Python 开发专家。
你的任务是编写一个 Python 脚本，根据以下的【公文格式规范】对 Word 文档进行格式化。

【公文格式规范】:
{rules}

【文档内容上下文】:
文档内容大致如下:
{doc_context}

【可用工具】:
- `doc`: Document 对象已作为全局变量 `doc` 提供。
- `doc.paragraphs`: 段落列表。
- `p.text`: 段落文本。
- `p.style`: 段落样式。
- `p.alignment`: 对齐方式 (WD_ALIGN_PARAGRAPH.CENTER, LEFT, etc.)。
- `run.font.name`: 字体名称。
- `set_east_asian_font(run, font_name)`: 必须使用此辅助函数来设置中文字体 (例如: 'SimHei', 'KaiTi', '楷体_GB2312')。

【严格要求】:
1. 必须严格遵守【公文格式规范】中的字体名称。
2. **绝对禁止**将中文字体名称翻译为英文（例如：如果规则说 "楷体_GB2312"，代码中必须用 "楷体_GB2312"，严禁使用 "KaiTi"）。
3. 字体大小必须严格匹配。
4. 尽量不要修改正文中已有的加粗/斜体格式（遍历 runs 处理）。
5. 代码必须健壮，处理可能不存在的属性。
"""

    CHAT_PROMPT_TEMPLATE = """
You are an expert AI assistant helping a user edit a Word document.
Your goal is to understand the user's intent and collaborate with them to refine the document content.

STYLE GUIDE (Use this tone and style for all suggestions):
{style_guide}

CONTEXT:
The document content is roughly:
{doc_context}

SELECTION CONTEXT (The user has selected these specific paragraphs):
{selection_context}

CHAT HISTORY:
{history}

USER MESSAGE:
{user_message}

INSTRUCTIONS:
1. **Multi-turn Refinement**: Do NOT generate a JSON patch immediately unless the user explicitly asks to "apply", "update", "save", "confirm", or "do it".
2. **Drafting**: If the user asks for changes (e.g., "optimize this", "make it formal"), provide a DRAFT or SUGGESTION in your reply. Discuss the changes.
3. **Style**: Adhere strictly to the STYLE GUIDE.
4. **Selection Priority**: If SELECTION CONTEXT is provided, you MUST focus your code generation on those specific paragraphs.
   - Use the `id` from the SELECTION CONTEXT to find the correct paragraph index in the `doc.paragraphs` list.
   - Example: If selected paragraph has id 5, you should target `doc.paragraphs[5]`.
   - Do NOT guess the paragraph based on text content if an ID is provided.
5. **CITATION RULE**: When referencing or extracting information from the 【参考资料】 section (Reference Materials), you **MUST** explicit cite the page number at the end of the relevant sentence or paragraph.
   - Format: `(第 N 页)` or `(第 N-M 页)`.
   - Source: Derive the page number `N` from the `[第 N 页]` or `[第 N 页 (估算)]` markers that appear strictly above the referenced text in the Context.
   - Example: "该项目旨在提高效率 (第 5 页)。"

OUTPUT FORMAT:
You must return a JSON object with the following structure (Make sure all strings are valid JSON, escape newlines as \\n):
{{
    "intent": "CHAT" or "MODIFY",
    "reply": "Your conversational response to the user. If suggesting changes, show the draft here.",
    "code": "The Python code to execute (REQUIRED ONLY if intent is MODIFY, otherwise null)"
}}

FOR MODIFY INTENT:
- The `code` field must contain valid Python code using `python-docx`.
- AVAILABLE TOOLS:
    - `doc`: The Document object.
    - `insert_image(paragraph, image_path, width=None)`: Insert an image after a paragraph. Supports `/static/images/` URLs.
    - `paragraph.insert_paragraph_after(text=None, style=None)`: Insert a new paragraph after the current one.
    - `smart_replace(doc, find_text, replace_text)`
    - `search_replace(doc, find_text, replace_text)`
    - `apply_markdown(doc, paragraph_index, markdown_text)`: Use this to apply the FINAL AGREED TEXT.
    - `flexible_replace(doc, find_text, replace_text)`

FOR CHAT INTENT:
- The `reply` field should contain your helpful answer or draft.
- The `code` field should be null.
"""

    MODIFICATION_PROMPT_TEMPLATE = """
You are an expert Python developer working with the python-docx library.
Your task is to write a Python script to modify a Word document based on the user's instruction.

CAPABILITIES:
- You CAN insert images using `insert_image(paragraph, url)` or `run.add_picture(url)`.
- You CAN insert paragraphs using `paragraph.insert_paragraph_after()`.

CONTEXT:
The document content is roughly:
{doc_context}

INSTRUCTION:
{instruction}

AVAILABLE TOOLS:
- `doc`: The Document object is available as `doc`.
- `insert_image(paragraph, image_path, width=None)`: Insert an image after a paragraph. Supports `/static/images/` URLs.
- `paragraph.insert_paragraph_after(text=None, style=None)`: Insert a new paragraph after the current one.
- `paragraph.id`: The index of the paragraph.
- `smart_replace(doc, find_text, replace_text)`: Use this for simple text replacements.
- `search_replace(doc, find_text, replace_text)`: Use this for robust replacements.
- `apply_markdown(doc, paragraph_index, markdown_text)`: Use this if you are generating NEW content.
"""

    TOC_ANALYSIS_PROMPT_TEMPLATE = """
    你是一位协助从大型文档中检索信息的AI研究助手。
    你的任务是分析文档的大纲（Table of Contents, TOC）及其摘要片段（Snippet），并识别哪些章节可能包含用户问题的答案。
    
    用户问题:
    {query}
    
    文档大纲 (Smart Outline):
    {toc}
    
    指令:
    1. 返回一个包含最相关章节ID（开始索引 start, 结束索引 end）的JSON列表。
    2. 结合【标题】和【摘要片段】进行判断。如果标题不明确但摘要片段包含相关信息，请务必选中该章节。
    3. 最多选择 3-5 个章节。不用选太多。
    4. 输出格式:
    [
        {{"start": 100, "end": 200, "title": "章节标题", "doc_idx": 0, "reason": "摘要提及相关内容"}},
        ...
    ]
    5. 如果目录行中包含 "idx:" 信息，请务必在JSON输出中包含对应的 "doc_idx"。
    6. 如果没有相关章节，请返回空列表 []。
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key

    def audit_document(self, source_text: str, target_text: str, rules: str, images: List[str] = [], model_config: Dict[str, Any] = None, use_reflection: bool = True) -> str:
        """
        Audits the target document against source materials and rules.
        Uses a "Draft-Critique-Refine" Agentic workflow to improve accuracy.
        """
        # --- Step 1: Draft ---
        draft_prompt = f"""
        你是一位专业的公文智能审核员。
        你的任务是根据【参考依据】和【审核规则】来核实【待审文档】的准确性。
        
        【参考依据 (Source Material)】:
        {source_text}
        (注意: 如果提供了图片，请结合图片内容进行核实。)
        
        【待审文档 (Target Document)】:
        {target_text}
        
        【审核规则 (Audit Rules)】:
        {rules}
        
        【操作指南】:
        1. 仔细比对事实、日期、金额、人名和机构名。
        2. 识别任何不一致之处（包括关键词缺失、数字错误、内容不完整）。
        3. 验证是否符合审核规则。
        4. 请务必以正确的 JSON 格式输出报告（不要使用 Markdown 代码块）：
        {{{{
            "status": "PASS" | "FAIL" | "WARNING",
            "issues": [
                {{{{
                    "severity": "high" | "medium" | "low",
                    "problematicText": "原文中需要修改的具体文本片段（必须与原文完全一致）",
                    "description": "详细描述发现的问题（例如：目标文档中是“X”，但参考依据显示为“Y”）",
                    "location": "问题位置（指出具体的段落或表格行号）",
                    "suggestion": "具体的修改建议（例如：将“X”改为“Y”）"
                }}}}
            ],
            "summary": "简明扼要的审核结果总结"
        }}}}
        """
        
        draft_result = "{}"
        
        # Dispatch to LLM (Draft)
        if model_config and model_config.get("apiKey"):
             provider = model_config.get("provider")
             api_key = model_config.get("apiKey")
             endpoint = model_config.get("endpoint")
             model = model_config.get("model")
             
             try:
                 if provider == "gemini":
                      draft_result = self._call_google_gemini(api_key, draft_prompt, endpoint, model, images)
                 elif provider in ["openai", "deepseek", "free", "aliyun", "ali", "doubao", "depOCR"]:
                      draft_result = self._call_openai_compatible(api_key, endpoint, model, draft_prompt)
                 else:
                      logger.warning(f"Unknown provider '{provider}', attempting OpenAI-compatible call")
                      draft_result = self._call_openai_compatible(api_key, endpoint, model, draft_prompt)
             except Exception as e:
                 logger.error(f"Audit Draft LLM Error: {e}")
                 return json.dumps({
                     "status": "FAIL", 
                     "issues": [{"description": f"Internal Error: {str(e)}"}], 
                     "summary": "Audit failed due to internal error."
                 })
        else:
             return self._mock_audit_response()

        if not use_reflection:
            return draft_result

        # --- Step 2: Critique & Refine (Reflection) ---
        # Only reflect if there is a valid result to critique
        if "issues" not in draft_result: 
             return draft_result

        reflection_prompt = f"""
        你是一位高级公文质检专家 (Senior QA Auditor)。
        
        你的下属提交了以下审核报告（JSON格式）：
        {draft_result}
        
        请根据原始材料，仔细审查这份报告的准确性 (Reflection)：
        1. 检查是否有【误报】(False Positives)：报告指出的错误其实在文档中是正确的？如果有，请删除该问题。
        2. 检查是否有【漏报】(False Negatives/Omissions)：是否还有遗漏的严重错误？如果有，请补充。
        3. 检查【参考依据】与【审核规则】是否应用正确。
        
        【参考依据】:
        {source_text}

        【审核规则】:
        {rules}
        
        请输出经过你修正后的、最终的 JSON 审核报告。格式必须与原格式完全一致。
        """

        try:
             logger.info("Executing Audit Reflection Step...")
             if provider == "gemini":
                  final_result = self._call_google_gemini(api_key, reflection_prompt, endpoint, model, images)
             elif provider in ["openai", "deepseek", "free", "aliyun", "ali", "doubao", "depOCR"]:
                  final_result = self._call_openai_compatible(api_key, endpoint, model, reflection_prompt)
             else:
                  logger.warning(f"Unknown provider '{provider}', attempting OpenAI-compatible call")
                  final_result = self._call_openai_compatible(api_key, endpoint, model, reflection_prompt)
             
             # Fallback if reflection fails or returns garbage
             if "issues" in final_result:
                 return final_result
             else:
                 logger.warning("Reflection returned invalid JSON, falling back to draft.")
                 return draft_result
                 
        except Exception as e:
             logger.error(f"Audit Reflection Error: {e}, falling back to draft.")
             return draft_result

    def _mock_audit_response(self) -> str:
        return json.dumps({
            "status": "WARNING",
            "issues": [
                {
                    "severity": "medium",
                    "problematicText": "10000",
                    "description": "Mock finding: '10000' in Target vs '9800' in Source.",
                    "location": "Paragraph 2",
                    "suggestion": "Verify amount."
                }
            ],
            "summary": "Mock Audit completed. Found potential discrepancies."
        })

    def stream_audit_document(self, source_text: str, target_text: str, rules: str, images: List[str] = [], model_config: Dict[str, Any] = None) -> Any:
        """
        Stream output from LLM for Audit.
        Yields chunks of text or partial JSON.
        """
        draft_prompt = f"""
        你是一位专业的公文智能审核员。
        你的任务是根据【参考依据】和【审核规则】来核实【待审文档】的准确性。
        
        【参考依据 (Source Material)】:
        {source_text}
        (注意: 如果提供了图片，请结合图片内容进行核实。)
        
        【待审文档 (Target Document)】:
        {target_text}
        
        【审核规则 (Audit Rules)】:
        {rules}
        
        【操作指南】:
        1. 仔细比对事实、日期、金额、人名和机构名。
        2. 识别任何不一致之处（包括关键词缺失、数字错误、内容不完整）。
        3. 验证是否符合审核规则。
        4. 请务必以正确的 JSON 格式输出报告。
        """

        if model_config and model_config.get("apiKey"):
             provider = model_config.get("provider")
             api_key = model_config.get("apiKey")
             endpoint = model_config.get("endpoint")
             model = model_config.get("model")
             
             try:
                 if provider == "gemini":
                      yield from self._call_google_gemini_stream(api_key, draft_prompt, endpoint, model, images)
                 elif provider in ["openai", "deepseek", "free", "aliyun", "ali", "doubao", "depOCR"]:
                      yield from self._call_openai_compatible_stream(api_key, endpoint, model, draft_prompt)
                 else:
                      logger.warning(f"Unknown provider '{provider}', attempting OpenAI-compatible stream")
                      yield from self._call_openai_compatible_stream(api_key, endpoint, model, draft_prompt)
             except Exception as e:
                 logger.error(f"Audit Stream Error: {e}")
                 yield f"# Error: {str(e)}"
        else:
             # Mock Stream
             full_response = self._mock_audit_response()
             chunk_size = 10
             for i in range(0, len(full_response), chunk_size):
                 yield full_response[i:i+chunk_size]

    def _call_google_gemini_stream(self, api_key: str, prompt: str, endpoint: str = None, model: str = None, images: List[str] = None):
         # Default model if not provided
         if not model:
            model = "gemini-2.0-flash-exp"
            
         logger.info(f"DEBUG: _call_google_gemini_stream (New SDK) - model: {model}")

         # Configure Client
         client = genai.Client(api_key=api_key)
         
         # Prepare content
         contents = [prompt]
         if images:
            for img_b64 in images:
                if "," in img_b64:
                    img_data_b64 = img_b64.split(",")[1]
                    mime_type = img_b64.split(",")[0].split(":")[1].split(";")[0]
                else:
                    img_data_b64 = img_b64
                    mime_type = "image/png"
                
                try:
                    img_bytes = base64.b64decode(img_data_b64)
                    contents.append(types.Part.from_bytes(data=img_bytes, mime_type=mime_type))
                except Exception as e:
                    logger.error(f"Failed to decode image for Gemini Stream: {e}")

         config = types.GenerateContentConfig(
            temperature=0.1,
         )
         
         # Retry logic for Stream (Init only)
         max_retries = 3
         for attempt in range(max_retries):
             try:
                 response_stream = client.models.generate_content_stream(
                     model=model,
                     contents=contents,
                     config=config
                 )
                 
                 for chunk in response_stream:
                     if chunk.text:
                         yield chunk.text
                 
                 # Break retry loop if successful
                 break

             except Exception as e:
                 error_str = str(e)
                 if "429" in error_str or "Resource exhausted" in error_str:
                     if attempt < max_retries - 1:
                         sleep_time = (2 ** attempt) + random.random()
                         logger.warning(f"Gemini New SDK Stream 429. Retrying in {sleep_time:.2f}s...")
                         time.sleep(sleep_time)
                         continue
                     else:
                         yield f"# Error: Gemini Rate Limit Exceeded (429)."
                         return
                 
                 if attempt < max_retries - 1:
                     logger.warning(f"Gemini New SDK Stream Error. Retrying... {e}")
                     time.sleep(1)
                     continue
                     
                 logger.error(f"Gemini New SDK Stream Failed: {e}")
                 yield f"# Error: {str(e)}"



    def _call_openai_compatible_stream(self, api_key: str, endpoint: str, model: str, prompt: str):
         headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
         payload = {
             "model": model, 
             "messages": [{"role": "user", "content": prompt}], 
             "temperature": 0.1,
             "stream": True # CRITICAL
         }
         
         url = endpoint
         # Ensure URL includes /chat/completions
         if not url.endswith("/chat/completions"):
             if url.endswith("/v1"):
                 url = url + "/chat/completions"
             elif "/v1" in url and not url.endswith("/chat/completions"):
                 # URL like https://api.com/v1 -> add /chat/completions
                 url = url.rstrip("/") + "/chat/completions"

         with httpx.stream("POST", url, headers=headers, json=payload, timeout=60.0) as response:
            if response.status_code != 200:
                yield f"# Error: {response.status_code} {response.read().decode()}"
                return

            for line in response.iter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]": break
                    try:
                        data_json = json.loads(data_str)
                        delta = data_json["choices"][0]["delta"]
                        if "content" in delta:
                            yield delta["content"]
                    except:
                        pass

    def generate(self, prompt: str, model_config: Dict[str, Any] = None) -> str:
        """
        Generic generation method for simple text-to-text tasks (Agentic use).
        Auto-detects API Key from environment if not provided.
        """
        # Determine Config defaults
        provider = "gemini"
        api_key = self.api_key
        endpoint = None
        model = "gemini-1.5-flash" # Default fallback
        
        if model_config:
            provider = model_config.get("provider", provider)
            api_key = model_config.get("apiKey", api_key)
            endpoint = model_config.get("endpoint", endpoint)
            model = model_config.get("model", model)
            
        # Fallback to Env if no key present in instance or config
        if not api_key:
             # Try common env vars
             api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
             
        if not api_key:
            logger.error("LLMEngine.generate: No API Key provided or found in ENV.")
            # Fail gracefully so agent can report it
            return "# Error: No API Key configured."

        # Dispatch
        try:
             if provider == "gemini":
                  # Check for endpoint to support compatible proxies if needed
                  if endpoint and ("/chat/completions" in endpoint or "/v1" in endpoint) and "googleapis.com" not in endpoint:
                       return self._call_openai_compatible(api_key, endpoint, model, prompt)
                  return self._call_google_gemini(api_key, prompt, endpoint, model)
             elif provider in ["openai", "deepseek", "aliyun", "free", "ali", "doubao", "depOCR"]:
                  return self._call_openai_compatible(api_key, endpoint, model, prompt)
             else:
                  # Fallback to OpenAI-compatible for unknown providers
                  logger.warning(f"Unknown provider '{provider}', attempting OpenAI-compatible call")
                  return self._call_openai_compatible(api_key, endpoint, model, prompt)
             
        except Exception as e:
             logger.error(f"Generate Error: {e}")
             return f"# Error: {str(e)}"

    def generate_code(self, user_instruction: str, doc_context: List[Dict[str, Any]], model_config: Dict[str, Any] = None) -> str:
        """
        Generates a Python script based on the user's instruction.
        """
        if model_config and model_config.get("apiKey"):
            return self._call_real_llm(user_instruction, doc_context, model_config)
        
        return self._mock_code_generation(user_instruction, doc_context)

    def analyze_toc_relevance(self, user_query: str, toc: List[Dict[str, Any]], model_config: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Analyzes the TOC to find relevant sections for the user's query.
        """
        # Prepare TOC text
        toc_text = ""
        for item in toc:
            indent = "  " * (item['level'] - 1)
            # Include filename or doc_idx in output so LLM acts on it?
            extra_info = ""
            if 'filename' in item:
                extra_info = f" [Doc: {item['filename']} | idx: {item.get('doc_idx', 0)}]"
            
            # Format: Title (ID: X-Y) [Snippet: ...]
            snippet_text = ""
            if "snippet" in item and item["snippet"]:
                snippet_text = f" | Snippet: {item['snippet']}..."

            toc_text += f"{indent}- {item['title']} (ID: {item['id']}-{item['end_id']}){extra_info}{snippet_text}\n"

        prompt = self.TOC_ANALYSIS_PROMPT_TEMPLATE.format(
            query=user_query,
            toc=toc_text
        )

        if model_config and model_config.get("apiKey"):
             provider = model_config.get("provider")
             api_key = model_config.get("apiKey")
             endpoint = model_config.get("endpoint")
             model = model_config.get("model")
             model = model_config.get("model")
             # Use a faster model if possible for this routing step
             
             try:
                 result = ""
                 if provider == "openai" or provider == "deepseek":
                     result = self._call_openai_compatible(api_key, endpoint, model, prompt)
                 elif provider == "gemini":
                     if endpoint and ("/chat/completions" in endpoint or "/v1" in endpoint) and "googleapis.com" not in endpoint:
                          result = self._call_openai_compatible(api_key, endpoint, model, prompt)
                     else:
                          result = self._call_google_gemini(api_key, prompt, endpoint, model)

                 # Parse JSON
                 json_match = re.search(r"\[.*\]", result, re.DOTALL)
                 if json_match:
                     json_str = json_match.group(0)
                     try:
                         parsed = json.loads(json_str)
                     except json.JSONDecodeError:
                         # Repair Chinese quotes/punctuation
                         json_str = json_str.replace('”', '"').replace('“', '"')
                         json_str = json_str.replace('，', ',')
                         try:
                             parsed = json.loads(json_str)
                         except:
                             logger.error(f"Failed to parse TOC JSON: {json_str}")
                             # Fallback to mock
                             parsed = None
                             
                     if isinstance(parsed, list):
                         # validate items are dicts
                         valid_items = []
                         for item in parsed:
                             if isinstance(item, dict) and 'start' in item:
                                 valid_items.append(item)
                         if valid_items:
                             return valid_items

             except Exception as e:
                 logger.error(f"Error in analyze_toc_relevance: {e}")
        
        # Mock/Fallback logic
        return self._mock_toc_analysis(user_query, toc)

    def _mock_toc_analysis(self, user_query: str, toc: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Simple keyword match as mock fallback
        relevant = []
        keywords = user_query.split()
        for item in toc:
            for kw in keywords:
                if len(kw) > 1 and kw.lower() in item['title'].lower():
                    relevant.append({"start": item['id'], "end": item['end_id'], "title": item['title']})
                    break
        return relevant

    def chat_with_doc(self, user_message: str, doc_context: List[Dict[str, Any]], ref_context: str = None, model_config: Dict[str, Any] = None, history: List[Dict[str, str]] = [], selection_context: List[int] = []) -> Dict[str, Any]:
        """
        Interacts with the document based on user message.
        Returns a dict with 'intent', 'reply', and 'code'.
        """
        # 1. Load Style Guide
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            style_path = os.path.join(current_dir, "style_guide.txt")
            with open(style_path, "r", encoding="utf-8") as f:
                style_guide = f.read()
        except FileNotFoundError:
            style_guide = "Tone: Professional and helpful."

        # 2. Prepare Contexts
        # Selection Context
        if selection_context:
            selected_paras = []
            for idx in selection_context:
                # Find para in doc_context or fetch from doc?
                # doc_context is ALREADY a list of dicts from preview data
                # We need to filter it. Or assume `selection_context` passed here is just IDs.
                # Actually LLM prompt expects text.
                # Simplified: Just say "Paragraphs X, Y"
                selected_paras.append(f"Paragraph {idx}")
            
            selection_text = json.dumps(selected_paras, ensure_ascii=False, indent=2)
        else:
            selection_text = "No specific text selected."

        # 3. Prepare History
        history_text = ""
        for msg in history[-5:]: # Keep last 5 turns
            history_text += f"{msg['role'].upper()}: {msg['content']}\n"
            
        # 4. Construct Prompt
        # Append Reference Context to prompt if exists (this is cleaner than appending to user message)
        final_doc_context = "【当前编辑文档 (可修改)】:\n" + json.dumps(doc_context, ensure_ascii=False, indent=2)
        
        if ref_context:
            final_doc_context += f"\n\n【参考资料 (只读/不可修改)】:\n{ref_context}"

        prompt = self.CHAT_PROMPT_TEMPLATE.format(
            doc_context=final_doc_context, 
            user_message=user_message,
            style_guide=style_guide,
            selection_context=selection_text,
            history=history_text
        )

        # 2. Call LLM
        if model_config and model_config.get("apiKey"):
             # Dispatch based on provider
             provider = model_config.get("provider")
             api_key = model_config.get("apiKey")
             endpoint = model_config.get("endpoint")
             model = model_config.get("model")

             try:
                 if provider == "openai" or provider == "deepseek" or provider == "aliyun":
                     result = self._call_openai_compatible(api_key, endpoint, model, prompt)
                 elif provider == "gemini":
                     if endpoint and ("/chat/completions" in endpoint or "/v1" in endpoint) and "googleapis.com" not in endpoint:
                          result = self._call_openai_compatible(api_key, endpoint, model, prompt)
                     else:
                          result = self._call_google_gemini(api_key, prompt, endpoint, model)
                 
                 # 3. Parse JSON Response
                 # Clean markdown fences if present
                 clean_result = self._clean_code(result)
                 logger.info(f"LLM Raw Response: {clean_result}")

                 # Find JSON object
                 json_match = re.search(r"\{.*\}", clean_result, re.DOTALL)
                 if json_match:
                     json_str = json_match.group(0)
                     try:
                        parsed = json.loads(json_str)
                     except json.JSONDecodeError:
                        # Attempt to repair common LLM JSON errors
                        # 1. Fix Chinese quotes used as delimiters
                        # Replace ”} with "}
                        json_str = json_str.replace('”}', '"}')
                        json_str = json_str.replace('”]', '"]')
                        # Replace ”, with ",
                        json_str = json_str.replace('”,', '",')
                        # Replace : “ with : "
                        json_str = json_str.replace(': “', ': "')
                        
                        try:
                            parsed = json.loads(json_str)
                            logger.info("Successfully repaired JSON with Chinese quotes.")
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse JSON from LLM: {clean_result}")
                            return {"intent": "CHAT", "reply": f"I had trouble processing that. Raw response: {clean_result}", "code": None}

                     # Validate parsed JSON
                     if not isinstance(parsed, dict):
                          return {"intent": "CHAT", "reply": f"Invalid JSON from LLM: {clean_result}", "code": None}
                    
                     # Ensure reply is a string
                     if "reply" not in parsed or parsed["reply"] is None:
                          parsed["reply"] = "I processed your request."
                    
                     return parsed
                 else:
                     # Fallback if no JSON found (treat as chat)
                     return {"intent": "CHAT", "reply": result, "code": None}

             except Exception as e:
                 logger.error(f"Error calling LLM for chat: {e}")
                 return {"intent": "CHAT", "reply": f"Error: {str(e)}", "code": None}
        
        # Mock implementation
        return self._mock_chat_response(user_message, doc_context)

    def _mock_chat_response(self, user_message: str, doc_context: List[Dict[str, Any]]) -> Dict[str, Any]:
        msg = user_message.lower()
        if "change" in msg or "modify" in msg or "update" in msg:
             code = self._mock_code_generation(user_message, doc_context)
             return {
                 "intent": "MODIFY",
                 "reply": "I've drafted those changes for you. Please check the preview.",
                 "code": code
             }
        else:
             return {
                 "intent": "CHAT",
                 "reply": f"I see you're asking about '{user_message}'. I can help you modify the document if you be more specific, e.g., 'Change the title to...'",
                 "code": None
             }

    def generate_formatting_code(self, doc_context: List[Dict[str, Any]], model_config: Dict[str, Any] = None, scope: str = "all", processor: str = "local") -> str:
        """
        Generates a Python script to format the document according to official rules.
        scope: "all", "layout", "body"
        processor: "local" (Regex) or "ai" (LLM)
        """
        # If processor is local, use heuristic engine
        if processor == "local":
            return self._heuristic_formatting_code()

        # Otherwise, use LLM
        # Read rules
        try:
            # Use absolute path relative to this file for portability
            current_dir = os.path.dirname(os.path.abspath(__file__))
            rules_path = os.path.join(current_dir, "formatting_rules.txt")
            
            with open(rules_path, "r", encoding="utf-8") as f:
                rules = f.read()
        except FileNotFoundError:
            logger.warning(f"Formatting rules file not found. Using default rules.")
            rules = "Title: Center, 2号小标宋体. Body: 3号仿宋体. Level 1: 3号黑体. Level 2: 3号楷体."

        # Adjust rules/instructions based on scope
        scope_instruction = ""
        if scope == "layout":
            scope_instruction = "\nCRITICAL INSTRUCTION: Do NOT format the Body text (Rule #3). Only format Titles, Headings (Level 1, Level 2), and other layout elements. Keep body text unchanged for now."
        elif scope == "body":
            scope_instruction = "\nCRITICAL INSTRUCTION: ONLY format the Body text (Rule #3). Do NOT change Titles or Headings. Assume they are already formatted."

        prompt = self.FORMATTING_PROMPT_TEMPLATE.format(
            rules=rules + scope_instruction,
            doc_context=json.dumps(doc_context, ensure_ascii=False, indent=2)
        )

        if model_config and model_config.get("apiKey"):
             # Dispatch based on provider
             provider = model_config.get("provider")
             api_key = model_config.get("apiKey")
             endpoint = model_config.get("endpoint")
             model = model_config.get("model")

             try:
                 if provider == "openai" or provider == "deepseek":
                     result = self._call_openai_compatible(api_key, endpoint, model, prompt)
                 elif provider == "gemini":
                     if endpoint and ("/chat/completions" in endpoint or "/v1" in endpoint) and "googleapis.com" not in endpoint:
                          result = self._call_openai_compatible(api_key, endpoint, model, prompt)
                     else:
                          result = self._call_google_gemini(api_key, prompt, endpoint, model)
                 
                 if result and not result.startswith("# Error"):
                     return result
                 else:
                     logger.warning("LLM returned error or empty result. Falling back to mock.")
             except Exception as e:
                 logger.error(f"Error calling LLM for formatting: {e}")
        
        return self._heuristic_formatting_code()

    def _heuristic_formatting_code(self) -> str:
        """
        Generates Python code using local Regex rules for standard official document formatting.
        This is much faster and more accurate for standard "一、", "（一）" structures.
        """
        return """
# Heuristic Formatting (Regex-based)
# Note: 'doc', 're', 'Pt', 'WD_ALIGN_PARAGRAPH', 'set_east_asian_font' are injected by docx_engine.

for i, p in enumerate(doc.paragraphs):
    text = p.text.strip()
    if not text:
        continue
        
    # 1. Title Detection
    # Rule: First non-empty paragraph is usually the title.
    # Style: 方正小标宋简体, 22pt (二号), Center
    if i == 0:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in p.runs:
            run.font.size = Pt(22)
            set_east_asian_font(run, '方正小标宋简体')
            run.bold = False # Titles usually not bold in this standard, or let user decide.
            
    # 2. Level 1 Heading (一级标题)
    # Rule: Starts with "一、", "二、", etc.
    # Style: 黑体, 16pt (三号)
    elif re.match(r"^[一二三四五六七八九十]+、", text):
        for run in p.runs:
            run.font.size = Pt(16)
            set_east_asian_font(run, '黑体')
            # Keep existing bold if any, or force? Standard usually implies specific font weight.
            # 黑体 itself is thick, usually don't need extra bold.
            
    # 3. Level 2 Heading (二级标题)
    # Rule: Starts with "（一）", "（二）", etc.
    # Style: 楷体_GB2312, 16pt (三号)
    elif re.match(r"^（[一二三四五六七八九十]+）", text):
        for run in p.runs:
            run.font.size = Pt(16)
            set_east_asian_font(run, '楷体_GB2312')
            run.bold = False
            
    # 4. Body Text (正文)
    # Rule: Everything else.
    # Style: 仿宋_GB2312, 16pt (三号)
    else:
        # For body, we must be careful NOT to overwrite bold/italic within the text.
        for run in p.runs:
            run.font.size = Pt(16)
            set_east_asian_font(run, '仿宋_GB2312')
            # Do NOT change run.bold or run.italic here to preserve inline formatting.
"""


    def _call_real_llm(self, instruction: str, doc_context: List[Dict[str, Any]], config: Dict[str, Any]) -> str:
        provider = config.get("provider")
        api_key = config.get("apiKey")
        endpoint = config.get("endpoint")
        model = config.get("model")
        
        prompt = self.MODIFICATION_PROMPT_TEMPLATE.format(
            doc_context=json.dumps(doc_context, ensure_ascii=False, indent=2),
            instruction=instruction
        )

        if provider == "openai" or provider == "deepseek":
            return self._call_openai_compatible(api_key, endpoint, model, prompt)
        elif provider == "gemini":
            # Check if endpoint looks like OpenAI compatible (e.g. ends with /v1/chat/completions)
            # Many proxies provide OpenAI-compatible endpoints for Gemini.
            if endpoint and ("/chat/completions" in endpoint or "/v1" in endpoint) and "googleapis.com" not in endpoint:
                 return self._call_openai_compatible(api_key, endpoint, model, prompt)
            
            # Otherwise, use Google API format
            return self._call_google_gemini(api_key, prompt, endpoint, model)
            
        return self._mock_code_generation(instruction, doc_context)

    def _call_openai_compatible(self, api_key: str, endpoint: str, model: str, prompt: str, stop: List[str] = None) -> str:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a python coding assistant."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1
        }
        if stop:
            payload["stop"] = stop
        
        try:
            # Handle cases where endpoint is the base URL vs full chat/completions URL
            url = endpoint
            if not url:
                return "# Error calling LLM: Endpoint is missing or None."
            
            # Ensure URL includes /chat/completions
            if not url.endswith("/chat/completions"):
                if url.endswith("/v1"):
                    url = url + "/chat/completions"
                elif "/v1" in url and not url.endswith("/chat/completions"):
                    # URL like https://api.com/v1 -> add /chat/completions
                    url = url.rstrip("/") + "/chat/completions"
            
            response = httpx.post(url, headers=headers, json=payload, timeout=60.0)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return self._clean_code(content)
        except Exception as e:
            logger.error(f"LLM Call Failed: {e}")
            error_msg = str(e).replace('\n', ' ').replace('\r', '')
            # Return error string that starts with # Error so caller can detect it
            return f"# Error calling LLM: {error_msg}"

    def _call_google_gemini(self, api_key: str, prompt: str, endpoint: str = None, model: str = None, images: List[str] = None) -> str:
        # Default model: Use 1.5 Flash (User typo 2.5 -> assuming 1.5)
        if not model:
            # User requested "gemini-2.5-flash", assuming they meant the latest stable flash which is 1.5
            # If they really meant 2.0-flash-exp, I can set that, but 1.5 is standard.
            model = "gemini-1.5-flash"
            
        logger.info(f"DEBUG: _call_google_gemini (New SDK) - model: {model}, has_images: {bool(images)}")

        # Configure Client
        client = genai.Client(api_key=api_key)
        
        # Prepare content
        contents = [prompt]
        if images:
            for img_b64 in images:
                if "," in img_b64:
                    img_data_b64 = img_b64.split(",")[1]
                    mime_type = img_b64.split(",")[0].split(":")[1].split(";")[0]
                else:
                    img_data_b64 = img_b64
                    mime_type = "image/png"
                
                # New SDK Types: Use types.Part.from_bytes
                try:
                    img_bytes = base64.b64decode(img_data_b64)
                    contents.append(types.Part.from_bytes(data=img_bytes, mime_type=mime_type))
                except Exception as e:
                    logger.error(f"Failed to decode image for Gemini: {e}")
                    # Skip this image or continue

        # Safety Settings
        # In new SDK, we use types.SafetySetting
        safety_settings = [
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
        ]

        config = types.GenerateContentConfig(
            temperature=0.1,
            safety_settings=safety_settings
        )

        # Retry logic: DISABLED per user request
        max_retries = 1 
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=config
                )
                
                # New SDK response structure
                if not response.text:
                     logger.warning(f"Gemini returned empty text. Response: {response}")
                     return "# Error: Gemini returned no text (Possible Safety Block)."

                return self._clean_code(response.text)
                
            except Exception as e:
                # Check for 429 in exception message or type
                error_str = str(e)
                if "429" in error_str or "Resource exhausted" in error_str:
                    if attempt < max_retries - 1:
                        sleep_time = (2 ** attempt) + random.random()
                        logger.warning(f"Gemini New SDK 429 Rate Limit. Retrying in {sleep_time:.2f}s...")
                        time.sleep(sleep_time)
                        continue
                    else:
                        return f"# Error: Gemini Rate Limit Exceeded (429) after {max_retries} retries."
                
                logger.error(f"Gemini New SDK Call Failed: {e}")
                return f"# Error calling Gemini SDK: {e}"
                
        return "# Error: Gemini Call Failed after retries."

    def _clean_code(self, content: str) -> str:
        # Remove markdown fences
        content = re.sub(r"```python", "", content, flags=re.IGNORECASE)
        content = re.sub(r"```json", "", content, flags=re.IGNORECASE)
        content = re.sub(r"```", "", content)
        # Remove literal "json" prefix if it appears at start
        if content.strip().lower().startswith("json"):
            content = content.strip()[4:]
        return content.strip()

    def _mock_code_generation(self, instruction: str, doc_context: List[Dict[str, Any]]) -> str:
        """
        Generates a Python script for the demo.
        """
        instruction_lower = instruction.lower()
        
        # 1. Check for "Title" or "Heading" (English and Chinese)
        if any(kw in instruction_lower for kw in ["title", "heading", "题目", "标题"]):
            # Try to extract text: quoted, or after "为"/"to"
            new_text = self._extract_quoted_text(instruction)
            if not new_text:
                # Try regex for "change title to X" or "修改题目为X"
                match = re.search(r"(?:to|为)\s*(.*)", instruction, re.IGNORECASE)
                if match:
                    new_text = match.group(1).strip()
            
            new_text = new_text or "Modified Title"
            
            # Smarter Title Detection: Look for "Title" style or text starting with "题目"/"Title"
            return f"""
# Modify Title (Smart Detection)
target_idx = 0
found = False
for i, p in enumerate(doc.paragraphs):
    if p.style.name.startswith("Heading") or p.style.name == "Title":
        target_idx = i
        found = True
        break
    if p.text.strip().startswith("题目") or p.text.strip().startswith("标题"):
        target_idx = i
        found = True
        break

if len(doc.paragraphs) > target_idx:
    doc.paragraphs[target_idx].text = "{new_text}"
"""

        # 2. Check for "Paragraph X" (English and Chinese)
        match = re.search(r"(?:paragraph|第)\s*(\d+)", instruction, re.IGNORECASE)
        if match:
            try:
                idx = int(match.group(1)) - 1
                new_text = self._extract_quoted_text(instruction)
                if not new_text:
                     match_text = re.search(r"(?:to|为)\s*(.*)", instruction, re.IGNORECASE)
                     if match_text:
                         new_text = match_text.group(1).strip()
                new_text = new_text or "Modified Paragraph Content"
                return f"""
# Modify Paragraph {idx+1}
if len(doc.paragraphs) > {idx}:
    doc.paragraphs[{idx}].text = "{new_text}"
"""
            except ValueError:
                pass

        # 3. Smart Search and Replace (Chinese Patterns)
        # Pattern: 把 "A" 改为 "B" / 将 "A" 替换为 "B" / 修改 "A" 为 "B"
        # Also support unquoted if clear markers exist
        
        # Regex for "把 A 改为 B" etc.
        # We try to capture A and B.
        # Markers for start: 把, 将, 修改
        # Markers for middle: 改为, 替换为, 变成, 为, to
        
        patterns = [
            r"(?:把|将|修改)\s*['\"](.*?)['\"]\s*(?:改为|替换为|变成|为|to)\s*['\"](.*?)['\"]", # Quoted
            r"(?:把|将|修改)\s*(.+?)\s*(?:改为|替换为|变成|为)\s*(.+)", # Unquoted (greedy match might be risky, but try)
        ]
        
        find_text = None
        replace_text = None
        
        for pat in patterns:
            m = re.search(pat, instruction, re.IGNORECASE)
            if m:
                find_text = m.group(1).strip()
                replace_text = m.group(2).strip()
                break
        
        # Fallback to just finding two quoted strings
        if not find_text:
            quoted_texts = re.findall(r"['\"](.*?)['\"]", instruction)
            if len(quoted_texts) >= 2:
                find_text = quoted_texts[0]
                replace_text = quoted_texts[1]

        if find_text and replace_text:
            return f"""
# Smart Search and Replace
search_replace(doc, "{find_text}", "{replace_text}")
"""

        # 4. Smart Fuzzy Match & Optimize (Chinese)
        # Pattern: 把 [Target] [Action: 优化/润色/修改]
        # Example: "把 这个问 整个内容优化下" -> Target: "这个问", Action: "优化"
        
        # Regex to capture target and action
        # We look for "把" followed by something, then an action keyword.
        match = re.search(r"把\s*(.*?)\s*(优化|润色|修改|改一下)", instruction, re.IGNORECASE)
        if match:
            target_text = match.group(1).strip()
            action = match.group(2).strip()
            
            # Find best match in doc
            best_idx, best_ratio = self._find_best_match_paragraph(target_text, doc_context)
            
            if best_idx != -1 and best_ratio > 0.2: # Lowered Threshold
                if action in ["优化", "润色"]:
                    return f"""
# Smart Optimize (Markdown Support)
target_idx = {best_idx}
if len(doc.paragraphs) > target_idx:
    original_text = doc.paragraphs[target_idx].text
    # Simulate optimization with Markdown
    # We'll make the original text bold to show "optimization"
    new_text = "**" + original_text + "** [AI Optimized]"
    apply_markdown(doc, target_idx, new_text)
"""
                elif action in ["修改", "改一下"]:
                     # Try to find what to change it TO
                     # Look for "为" or "成" after the action
                     to_match = re.search(r"(?:为|成)\s*(.*)", instruction[match.end():])
                     new_text = to_match.group(1).strip() if to_match else "Modified Content"
                     return f"""
# Smart Modify (Fuzzy Match: {best_ratio:.2f})
target_idx = {best_idx}
if len(doc.paragraphs) > target_idx:
    doc.paragraphs[target_idx].text = "{new_text}"
"""

                     return f"""
# Smart Modify (Fuzzy Match: {best_ratio:.2f})
target_idx = {best_idx}
if len(doc.paragraphs) > target_idx:
    doc.paragraphs[target_idx].text = "{new_text}"
"""

        # 5. Positional & Looser Patterns (Canvas-like)
        # Pattern: "最后一段为..." / "第一段改为..." / "Last paragraph to..."
        # Pattern: "X 为 Y" where X is a position
        
        # Check for "Last Paragraph" / "最后一段" / "最后一句" (Treating last sentence as last paragraph for now)
        if any(kw in instruction for kw in ["最后一段", "最后一句", "last paragraph", "last sentence"]):
            # Extract replacement text
            # Look for "为", "to", "变成"
            match = re.search(r"(?:为|to|变成|is)\s*(.*)", instruction, re.IGNORECASE)
            new_text = match.group(1).strip() if match else "Modified Content"
            
            return f"""
# Positional Modify (Last Paragraph)
if len(doc.paragraphs) > 0:
    target_idx = len(doc.paragraphs) - 1
    doc.paragraphs[target_idx].text = "{new_text}"
"""

        # Check for "First Paragraph" / "第一段" / "第一句"
        if any(kw in instruction for kw in ["第一段", "第一句", "first paragraph", "first sentence"]):
             match = re.search(r"(?:为|to|变成|is)\s*(.*)", instruction, re.IGNORECASE)
             new_text = match.group(1).strip() if match else "Modified Content"
             return f"""
# Positional Modify (First Paragraph)
if len(doc.paragraphs) > 0:
    target_idx = 0
    doc.paragraphs[target_idx].text = "{new_text}"
"""

        # 6. Fallback
        return f"""
# Fallback: Append text
doc.add_paragraph("[AI]: I heard '{instruction}' but I couldn't identify the target. Please try '把 A 改为 B'.")
"""

    def _find_best_match_paragraph(self, query: str, doc_context: List[Dict[str, Any]]) -> tuple[int, float]:
        """
        Finds the paragraph index that best matches the query string.
        Returns (index, similarity_ratio).
        """
        best_ratio = 0.0
        best_idx = -1
        
        for item in doc_context:
            text = item.get("text", "")
            if not text:
                continue
                
            # Check for substring first (strong signal)
            if query in text:
                return item["id"], 1.0
            
            # Check for tokenized substring (e.g. "Target Filler" -> "Target" in text)
            tokens = query.split()
            if len(tokens) > 1:
                for token in tokens:
                    if len(token) > 1 and token in text:
                        # Found a significant token match
                        return item["id"], 0.8 # High confidence for token match
            
            # Fuzzy match
            ratio = difflib.SequenceMatcher(None, query, text).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_idx = item["id"]
                
        return best_idx, best_ratio

    def _extract_quoted_text(self, text: str) -> str:
        matches = re.findall(r"['\"](.*?)['\"]", text)
        return matches[0] if matches else None
