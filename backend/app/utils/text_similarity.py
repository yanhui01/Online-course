"""文本相似度工具 — 用于题库模糊匹配"""

import hashlib
import re
from difflib import SequenceMatcher


def hash_question(text: str) -> str:
    """标准化题目文本后计算 SHA256 哈希"""
    normalized = normalize_text(text)
    return hashlib.sha256(normalized.encode()).hexdigest()


def normalize_text(text: str) -> str:
    """标准化文本：去空格、去标点、小写"""
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[，。！？、；：""''（）《》【】\.\,\!\?\;\:\"\'\(\)\[\]\{\}]", "", text)
    return text.lower()


def similarity(text1: str, text2: str) -> float:
    """计算两段文本的相似度 0.0 - 1.0"""
    return SequenceMatcher(None, normalize_text(text1), normalize_text(text2)).ratio()
