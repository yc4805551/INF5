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
        
        return issues

    def get_typos_text(self) -> str:
        """Returns a string representation of typos for LLM prompt context."""
        if not self.typos_map:
            return ""
        return ", ".join([f"{k}->{v}" for k, v in self.typos_map.items()])

    def get_forbidden_text(self) -> str:
        """Returns a string representation of forbidden words for LLM prompt context."""
        if not self.forbidden_words:
            return ""
        return ", ".join(self.forbidden_words)
