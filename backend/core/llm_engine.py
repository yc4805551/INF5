import json
import re
import difflib
import httpx
import logging
import os
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

OUTPUT FORMAT:
You must return a JSON object with the following structure:
{{
    "intent": "CHAT" or "MODIFY",
    "reply": "Your conversational response to the user. If suggesting changes, show the draft here.",
    "code": "The Python code to execute (REQUIRED ONLY if intent is MODIFY, otherwise null)"
}}

FOR MODIFY INTENT:
- The `code` field must contain valid Python code using `python-docx`.
- AVAILABLE TOOLS:
    - `doc`: The Document object.
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

CONTEXT:
The document content is roughly:
{doc_context}

INSTRUCTION:
{instruction}

AVAILABLE TOOLS:
- `doc`: The Document object is available as `doc`.
- `smart_replace(doc, find_text, replace_text)`: Use this for simple text replacements.
- `search_replace(doc, find_text, replace_text)`: Use this for robust replacements (multiple occurrences, split runs).
- `apply_markdown(doc, paragraph_index, markdown_text)`: Use this if you are generating NEW content or rewriting a paragraph. It supports **bold** and *italic*.

REQUIREMENTS:
1. Write ONLY the Python code. No markdown fences (```python), no explanations.
2. Do not assume any other variables exist.
3. Use the provided tools where appropriate.
"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key

    def generate_code(self, user_instruction: str, doc_context: List[Dict[str, Any]], model_config: Dict[str, Any] = None) -> str:
        """
        Generates a Python script based on the user's instruction.
        """
        if model_config and model_config.get("apiKey"):
            return self._call_real_llm(user_instruction, doc_context, model_config)
        
        return self._mock_code_generation(user_instruction, doc_context)

    def chat_with_doc(self, user_message: str, doc_context: List[Dict[str, Any]], model_config: Dict[str, Any] = None, history: List[Dict[str, str]] = [], selection_context: List[int] = []) -> Dict[str, Any]:
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

        # 2. Prepare Selection Context
        selection_text = ""
        if selection_context:
            selected_paras = [p for p in doc_context if p["id"] in selection_context]
            selection_text = json.dumps(selected_paras, ensure_ascii=False, indent=2)
        else:
            selection_text = "No specific text selected."

        # 3. Prepare History
        history_text = ""
        for msg in history[-5:]: # Keep last 5 turns
            history_text += f"{msg['role'].upper()}: {msg['content']}\n"

        # 4. Construct Prompt
        prompt = self.CHAT_PROMPT_TEMPLATE.format(
            doc_context=json.dumps(doc_context, ensure_ascii=False, indent=2),
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
                     try:
                        parsed = json.loads(json_match.group(0))
                        # Validate parsed JSON
                        if not isinstance(parsed, dict):
                             return {"intent": "CHAT", "reply": f"Invalid JSON from LLM: {clean_result}", "code": None}
                        
                        # Ensure reply is a string
                        if "reply" not in parsed or parsed["reply"] is None:
                             parsed["reply"] = "I processed your request."
                        
                        return parsed
                     except json.JSONDecodeError:
                        logger.error(f"Failed to parse JSON from LLM: {clean_result}")
                        return {"intent": "CHAT", "reply": f"I had trouble processing that. Raw response: {clean_result}", "code": None}
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

    def _call_openai_compatible(self, api_key: str, endpoint: str, model: str, prompt: str) -> str:
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
        
        try:
            # Handle cases where endpoint is the base URL vs full chat/completions URL
            url = endpoint
            if not url.endswith("/chat/completions") and "v1" not in url:
                 # Naive fix, but user provided full URL in .env example
                 pass
            
            response = httpx.post(url, headers=headers, json=payload, timeout=30.0)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return self._clean_code(content)
        except Exception as e:
            logger.error(f"LLM Call Failed: {e}")
            error_msg = str(e).replace('\n', ' ').replace('\r', '')
            # Return error string that starts with # Error so caller can detect it
            return f"# Error calling LLM: {error_msg}"

    def _call_google_gemini(self, api_key: str, prompt: str, endpoint: str = None, model: str = None) -> str:
        # Default model if not provided
        if not model:
            model = "gemini-2.5-flash"
            
        logger.info(f"DEBUG: _call_google_gemini - endpoint: {endpoint}, model: {model}")
        
        # Default URL if not provided or if it's just a base URL
        base_url = endpoint or "https://generativelanguage.googleapis.com/v1beta/models"
        
        # Construct full URL if needed
        # If endpoint is just base, append model and action
        if "generateContent" not in base_url:
            # Strip trailing slash
            base_url = base_url.rstrip("/")
            # If model is not in URL, append it
            if model not in base_url:
                 url = f"{base_url}/{model}:generateContent?key={api_key}"
            else:
                 url = f"{base_url}:generateContent?key={api_key}"
        else:
            url = f"{base_url}?key={api_key}"

        logger.info(f"Calling Gemini API: {url.split('?')[0]}...") # Log URL without key

        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        try:
            response = httpx.post(url, headers=headers, json=payload, timeout=60.0, verify=False)
            response.raise_for_status()
            data = response.json()
            # Handle safety ratings blocking content
            if "candidates" not in data or not data["candidates"]:
                 logger.error(f"Gemini blocked content or returned no candidates. Response: {json.dumps(data)}")
                 return f"# Error: Gemini blocked content or returned no candidates. Response: {json.dumps(data)}"
            
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            return self._clean_code(content)
        except Exception as e:
            logger.error(f"Gemini Call Failed: {e}")
            error_msg = str(e).replace('\n', ' ').replace('\r', '')
            return f"# Error calling Gemini: {error_msg}"

    def _clean_code(self, content: str) -> str:
        # Remove markdown fences
        content = re.sub(r"```python", "", content, flags=re.IGNORECASE)
        content = re.sub(r"```", "", content)
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
