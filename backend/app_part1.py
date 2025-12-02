import os
import logging
import json
import re
import hashlib
import uuid
import time
import io
import requests
import httpx
import difflib
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from dotenv import load_dotenv
from pymilvus import connections, Collection, utility, FieldSchema, DataType, CollectionSchema
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from docx import Document
import click

# Import DocxEngine from core
from core.docx_engine import DocxEngine
from core.llm_engine import LLMEngine

load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
MODEL_MAPPING = {
    "kb_qwen": "qwen-plus",
    "kb_nomic": "nomic-embed-text"
}
DEFAULT_EMBEDDING_MODEL = "nomic-embed-text"

# Ali/Qwen Configuration
ALI_API_KEY = os.getenv("ALI_API_KEY")
ALI_TARGET_URL = os.getenv("ALI_TARGET_URL", "https://dashscope.aliyuncs.com/compatible-mode")
ALI_MODEL = os.getenv("ALI_MODEL", "qwen-plus")

MILVUS_HOST = os.getenv("MILVUS_HOST", "127.0.0.1")
# 自动清理 http/https 前缀，防止连接失败
if MILVUS_HOST.startswith("http://"):
    MILVUS_HOST = MILVUS_HOST.replace("http://", "")
elif MILVUS_HOST.startswith("https://"):
    MILVUS_HOST = MILVUS_HOST.replace("https://", "")

MILVUS_PORT_STR = os.getenv("MILVUS_PORT", "19530")
try:
    MILVUS_PORT = int(MILVUS_PORT_STR)
except ValueError:
    logging.warning(f"MILVUS_PORT '{MILVUS_PORT_STR}' 无效, 使用默认值 19530")
    MILVUS_PORT = 19530

# --- Ollama 配置修复 (解决 502 Bad Gateway) ---
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1")

# 1. 强制修复 Windows 下无法访问 0.0.0.0 的问题
if "0.0.0.0" in OLLAMA_HOST:
    logging.warning(f"检测到 OLLAMA_HOST 为 0.0.0.0，正在自动转换为 127.0.0.1 以确保连接成功。")
    OLLAMA_HOST = OLLAMA_HOST.replace("0.0.0.0", "127.0.0.1")

# 2. 补全协议头
if not OLLAMA_HOST.startswith("http"):
    OLLAMA_HOST = f"http://{OLLAMA_HOST}"

OLLAMA_PORT = os.getenv("OLLAMA_PORT", "11434")
OLLAMA_EMBED_API_URL = f"{OLLAMA_HOST}:{OLLAMA_PORT}/api/embeddings"
logging.info(f"Ollama API 地址已配置为: {OLLAMA_EMBED_API_URL}")

# --- 知识库路径 ---
KNOWLEDGE_BASE_DIR = os.getenv("KNOWLEDGE_BASE_DIR", "./knowledge_base")
KNOWLEDGE_BASE_DIR_NOMIC = os.getenv("KNOWLEDGE_BASE_DIR_NOMIC", "./knowledge_base_nomic")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 500))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 50))
INGEST_WORKERS = int(os.getenv("INGEST_WORKERS", 8))

# --- AI 代理配置 ---

# Gemini (OpenAI 兼容模式)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("VITE_GEMINI_API_KEY")
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "dummy-key-for-proxy")
OPENAI_TARGET_URL = os.getenv("OPENAI_TARGET_URL", "https://api.chatanywhere.tech")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5") # 注意: gpt-5 目前可能只是占位符或特定渠道模型
# DeepSeek
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "dummy-key-for-proxy")
DEEPSEEK_TARGET_URL = os.getenv("DEEPSEEK_TARGET_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_ENDPOINT = os.getenv("DEEPSEEK_ENDPOINT", "https://api.deepseek.com/v1/chat/completions")

current_engine = DocxEngine()
llm_engine = LLMEngine()
