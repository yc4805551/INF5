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
        # 2. 从环境变量读取兜底（Fallback）
        provider_upper = provider.upper()
        api_key = api_key or os.getenv(f"{provider_upper}_API_KEY") or os.getenv(f"VITE_{provider_upper}_API_KEY")
        endpoint = endpoint or os.getenv(f"{provider_upper}_ENDPOINT") or os.getenv(f"VITE_{provider_upper}_ENDPOINT")
        model = model or os.getenv(f"{provider_upper}_MODEL") or os.getenv(f"VITE_{provider_upper}_MODEL")

        # 为了兼容历史特定环境变量配置，依旧可以保留特殊的默认 fallback
        if provider == "gemini":
            endpoint = endpoint or "https://generativelanguage.googleapis.com/v1beta/models"
            model = model or "gemini-2.0-flash-exp"
        elif provider == "openai":
            endpoint = endpoint or "https://api.openai.com/v1"
            model = model or "gpt-4"
        elif provider == "deepseek":
            endpoint = endpoint or "https://api.deepseek.com/v1"
            model = model or "deepseek-chat"
        
        if not api_key:
            raise ValueError(f"API key for {provider} not found in modelConfig or environment variables")
        
        # 构造完整的 prompt
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        if json_mode:
            full_prompt += "\n\n请仅返回 JSON 格式的结果，不要包含任何其他解释文字。"
        
        # 使用 LLMEngine 调用模型
        engine = LLMEngine()
        
        # 根据提供商选择调用方法
        if provider == "gemini" and endpoint and "googleapis.com" in endpoint:
            # 如果是官方 gemini endpoint, 使用旧有 google gemini SDK 逻辑
            response = engine._call_google_gemini(api_key, full_prompt, endpoint, model)
        else:
            # 默认所有未显式定义特殊处理的模型，或者使用了代理endpoint的Gemini，视为 OpenAI 兼容格式
            logger.info(f"Using OpenAI-compatible logic for File Search provider: {provider}")
            response = engine._call_openai_compatible(api_key, endpoint, model, full_prompt)
        
        return response
    
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        raise
