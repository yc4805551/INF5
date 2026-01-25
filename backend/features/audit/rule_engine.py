import os
import uuid
from typing import List, Dict, Any, Tuple

# Path to dictionaries
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
TYPOS_FILE = os.path.join(DATA_DIR, 'typos.txt')
FORBIDDEN_FILE = os.path.join(DATA_DIR, 'forbidden.txt')

class RuleEngine:
    def __init__(self):
        self.typos_map = self._load_typos()
        self.custom_map = self._load_custom_corrections()
        self.forbidden_words = self._load_forbidden()

    def _load_typos(self) -> Dict[str, str]:
        typos = {}
        if os.path.exists(TYPOS_FILE):
            with open(TYPOS_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split(',')
                    if len(parts) == 2:
                        typos[parts[0].strip()] = parts[1].strip()
        return typos

    def _load_custom_corrections(self) -> Dict[str, str]:
        custom = {}
        # User requested filename: 常见错误修改.txt
        custom_file = os.path.join(DATA_DIR, '常见错误修改.txt')
        if os.path.exists(custom_file):
            try:
                with open(custom_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'): continue
                        
                        parts = line.split(',')
                        if len(parts) >= 2:
                            wrong = parts[0].strip()
                            correct = parts[1].strip()
                            if wrong and correct:
                                custom[wrong] = correct
            except Exception as e:
                print(f"Error loading custom corrections: {e}")
        return custom

    def _load_forbidden(self) -> List[str]:
        words = []
        if os.path.exists(FORBIDDEN_FILE):
            with open(FORBIDDEN_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    word = line.strip()
                    if word:
                        words.append(word)
        return words

    def run_checks(self, text: str) -> List[Dict[str, Any]]:
        issues = []
        
        # 1. Check Typos
        for wrong, correct in self.typos_map.items():
            if wrong in text:
                issues.append({
                    "id": str(uuid.uuid4())[:8],
                    "type": "proofread", # Tag as proofread
                    "severity": "medium",
                    "original": wrong,
                    "suggestion": correct,
                    "reason": f"监测到易错词：'{wrong}' 应为 '{correct}'"
                })

        # 1.5 Check Custom Corrections
        for wrong, correct in self.custom_map.items():
            if wrong in text:
                issues.append({
                    "id": str(uuid.uuid4())[:8],
                    "type": "proofread",
                    "severity": "high", # Custom rules should be high priority
                    "original": wrong,
                    "suggestion": correct,
                    "reason": f"监测到自定义纠错：'{wrong}' 应为 '{correct}'"
                })

        # 2. Check Forbidden Words
        for word in self.forbidden_words:
            if word in text:
                issues.append({
                    "id": str(uuid.uuid4())[:8],
                    "type": "terminology",  # Tag as sensitive/terminology
                    "severity": "high",
                    "original": word,
                    "suggestion": "**DELETED**",
                    "reason": f"监测到敏感词/禁词：'{word}'，请移除。"
                })

        # 3. Check for Mixed Digits in Chinese (e.g., 测1试)
        import re
        # Pattern: Chinese char + 1 or more digits + Chinese char
        mixed_digit_matches = re.finditer(r'([\u4e00-\u9fa5])(\d+)([\u4e00-\u9fa5])', text)
        for match in mixed_digit_matches:
            detected = match.group(0)
            correction = match.group(1) + match.group(3) # Remove digit
            issues.append({
                "id": str(uuid.uuid4())[:8],
                "type": "proofread",
                "severity": "high",
                "original": detected.strip(), # Ensure no whitespace
                "problematicText": detected.strip(), # Explicit for replacement
                "suggestion": correction,
                "reason": "监测到中文词语中夹杂数字，可能是OCR或输入错误。"
            })
        
        # Note: 搭配不当等复杂语法问题交由 AI (Proofread Agent) 处理
        # 规则引擎只负责简单的模式匹配，避免过度硬编码
        
        return issues

    def get_typos_text(self) -> str:
        """Returns a string representation of typos for LLM prompt context."""
        combined = {**self.typos_map, **self.custom_map}
        if not combined:
            return ""
        return ", ".join([f"{k}->{v}" for k, v in combined.items()])

    def get_forbidden_text(self) -> str:
        """Returns a string representation of forbidden words for LLM prompt context."""
        if not self.forbidden_words:
            return ""
        return ", ".join(self.forbidden_words)
