"""
简单的 LLM 调用包装函数
供 search_agent 使用
"""
import logging
import os
from core.llm_engine import LLMEngine

logger = logging.getLogger(__name__)


def call_llm(
    provider: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.3,
    json_mode: bool = False,
    model_config: dict = None
) -> str:
    """
    调用大语言模型
    
    Args:
        provider: 模型提供商（gemini/openai/deepseek等）
        system_prompt: 系统提示
        user_prompt: 用户提示
        temperature: 温度（0-1，越低越确定）
        json_mode: 是否要求返回 JSON 格式
        model_config: 可选的模型配置（包含 apiKey, endpoint, model 等信息）
        
    Returns:
        模型响应文本
    """
    try:
        api_key = None
        endpoint = None
        model = None
        
        # 1. 优先尝试从传入的 model_config 解析配置
        if model_config and isinstance(model_config, dict):
            api_key = model_config.get("apiKey")
            model = model_config.get("model")
            
            # 部分模型 endpoint 可能在 modelConfig 里为空并且有个默认逻辑，所以有条件的合并
            if model_config.get("endpoint"):
                endpoint = model_config.get("endpoint")
        
        # 2. 从环境变量读取兜底（Fallback）
        if provider == "gemini":
            api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("VITE_GEMINI_API_KEY")
            endpoint = endpoint or os.getenv("GEMINI_ENDPOINT") or os.getenv("VITE_GEMINI_ENDPOINT") or "https://generativelanguage.googleapis.com/v1beta/models"
            model = model or os.getenv("GEMINI_MODEL") or os.getenv("VITE_GEMINI_MODEL") or "gemini-2.0-flash-exp"
        elif provider == "openai":
            api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("VITE_OPENAI_API_KEY")
            endpoint = endpoint or os.getenv("OPENAI_ENDPOINT") or os.getenv("VITE_OPENAI_ENDPOINT") or "https://api.openai.com/v1"
            model = model or os.getenv("OPENAI_MODEL") or os.getenv("VITE_OPENAI_MODEL") or "gpt-4"
        elif provider == "deepseek":
            api_key = api_key or os.getenv("DEEPSEEK_API_KEY") or os.getenv("VITE_DEEPSEEK_API_KEY")
            endpoint = endpoint or os.getenv("DEEPSEEK_ENDPOINT") or os.getenv("VITE_DEEPSEEK_ENDPOINT") or "https://api.deepseek.com/v1"
            model = model or os.getenv("DEEPSEEK_MODEL") or os.getenv("VITE_DEEPSEEK_MODEL") or "deepseek-chat"
        elif provider == "free":
            # Support for custom 'free' provider defined in .env.local
            api_key = api_key or os.getenv("FREE_API_KEY") or os.getenv("VITE_FREE_API_KEY")
            endpoint = endpoint or os.getenv("FREE_ENDPOINT") or os.getenv("VITE_FREE_ENDPOINT")
            model = model or os.getenv("FREE_MODEL") or os.getenv("VITE_FREE_MODEL")
        
        if not api_key:
            raise ValueError(f"API key for {provider} not found in modelConfig or environment variables")
        
        # 构造完整的 prompt
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        if json_mode:
            full_prompt += "\n\n请仅返回 JSON 格式的结果，不要包含任何其他解释文字。"
        
        # 使用 LLMEngine 调用模型
        engine = LLMEngine()
        model_config = {
            "provider": provider,
            "apiKey": api_key,
            "endpoint": endpoint,
            "model": model
        }
        
        # 根据提供商选择调用方法
        if provider == "gemini":
            response = engine._call_google_gemini(api_key, full_prompt, endpoint, model)
        elif provider in ["openai", "deepseek", "free"]:
            response = engine._call_openai_compatible(api_key, endpoint, model, full_prompt)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
        
        return response
    
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        raise
