import os
import uuid
from typing import List, Dict, Any, Tuple

# Path to dictionaries
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
TYPOS_FILE = os.path.join(DATA_DIR, '易错词纠正.txt')
FORBIDDEN_FILE = os.path.join(DATA_DIR, '禁词检查.txt')
ABBREVIATIONS_FILE = os.path.join(DATA_DIR, '术语简称.txt')

class RuleEngine:
    def __init__(self):
        self.typos_map = self._load_typos()
        self.custom_map = self._load_custom_corrections()
        self.forbidden_words = self._load_forbidden()
        self.abbreviations_text = self._load_abbreviations_raw()

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

    def _load_abbreviations_raw(self) -> str:
        """Loads the content of the abbreviations file as a single string for LLM context."""
        if os.path.exists(ABBREVIATIONS_FILE):
             try:
                with open(ABBREVIATIONS_FILE, 'r', encoding='utf-8') as f:
                    # Read all, maybe limit length if it gets huge, but for now just read.
                    return f.read()
             except Exception:
                 pass
        return ""

    def run_checks(self, text: str) -> List[Dict[str, Any]]:
        issues = []
        
        # 1. Check Typos (易错词纠正.txt)
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

        # 2. Check Custom Corrections (常见错误修改.txt)
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

        # 3. Check Forbidden Words (禁词检查.txt)
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


        # Note: 搭配不当等复杂语法问题交由 AI (Proofread Agent) 处理
        # 规则引擎只负责简单的模式匹配，避免过度硬编码
        # 
        # 已移除：中文夹杂数字检测规则（第96-111行）
        # 原因：会误报合理表达如"24小时"、"开通了24h时咨询热线"
        # 此类问题应交由 AI Agent 智能判断
        
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

    def get_abbreviations_text(self) -> str:
        """Returns a string representation of abbreviations for LLM prompt context."""
        return self.abbreviations_text
