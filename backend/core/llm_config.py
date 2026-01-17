"""
统一LLM配置管理
集中管理所有大模型provider的配置，支持多种来源优先级
"""
import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class LLMConfigManager:
    """
    LLM配置管理器
    优先级: config.json > 环境变量 > 默认值
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: config.json路径，默认为 config/llm_config.json
        """
        if config_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(base_dir, 'config', 'llm_config.json')
        
        self.config_path = config_path
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    logger.info(f"Loaded LLM config from {self.config_path}")
                    return config
            except Exception as e:
                logger.warning(f"Failed to load config from {self.config_path}: {e}")
        
        logger.info("Using default LLM config")
        return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """默认配置"""
        return {
            "default_provider": "gemini",
            "providers": {
                "gemini": {
                    "api_key": "",
                    "endpoint": "https://generativelanguage.googleapis.com/v1beta/models",
                    "model": "gemini-2.0-flash-exp"
                },
                "openai": {
                    "api_key": "",
                    "endpoint": "https://api.openai.com/v1",
                    "model": "gpt-3.5-turbo"
                },
                "deepseek": {
                    "api_key": "",
                    "endpoint": "https://api.deepseek.com/v1",
                    "model": "deepseek-chat"
                },
                "aliyun": {
                    "api_key": "",
                    "endpoint": "",
                    "model": "qwen-plus"
                }
            }
        }
    
    def get_provider_config(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """
        获取指定provider的配置
        
        Args:
            provider: provider名称，如果为None则使用默认provider
        
        Returns:
            配置字典 {"api_key": ..., "endpoint": ..., "model": ...}
        """
        if provider is None:
            provider = self._config.get("default_provider", "gemini")
        
        # 1. 从config.json获取基础配置
        provider_config = self._config.get("providers", {}).get(provider, {})
        
        # 2. 环境变量覆盖（兼容旧代码）
        env_prefix_map = {
            "gemini": ("GOOGLE", "GEMINI"),
            "openai": ("OPENAI",),
            "deepseek": ("DEEPSEEK",),
            "aliyun": ("ALI",)
        }
        
        env_prefixes = env_prefix_map.get(provider, ())
        
        # 尝试从环境变量读取
        for prefix in env_prefixes:
            api_key = os.getenv(f"VITE_{prefix}_API_KEY") or os.getenv(f"{prefix}_API_KEY")
            if api_key and not provider_config.get("api_key"):
                provider_config["api_key"] = api_key
            
            endpoint = (os.getenv(f"VITE_{prefix}_ENDPOINT") or 
                       os.getenv(f"{prefix}_ENDPOINT") or
                       os.getenv(f"{prefix}_BASE_URL"))
            if endpoint and not provider_config.get("endpoint"):
                provider_config["endpoint"] = endpoint
            
            model = os.getenv(f"VITE_{prefix}_MODEL") or os.getenv(f"{prefix}_MODEL_NAME")
            if model and not provider_config.get("model"):
                provider_config["model"] = model
        
        return {
            "provider": provider,
            "apiKey": provider_config.get("api_key", ""),
            "endpoint": provider_config.get("endpoint", ""),
            "model": provider_config.get("model", "")
        }
    
    def resolve_config(self, model_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析并补全model_config
        
        Args:
            model_config: 前端传入的配置（可能不完整）
        
        Returns:
            完整的配置字典
        """
        # 1. 确定provider
        provider = model_config.get("provider")
        if not provider:
            # 根据环境变量自动检测
            if os.getenv("VITE_DEEPSEEK_API_KEY") or os.getenv("DEEPSEEK_API_KEY"):
                provider = "deepseek"
            elif os.getenv("VITE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY"):
                provider = "openai"
            elif os.getenv("VITE_ALI_API_KEY") or os.getenv("ALI_API_KEY"):
                provider = "aliyun"
            else:
                provider = self._config.get("default_provider", "gemini")
        
        # 2. 获取完整配置
        full_config = self.get_provider_config(provider)
        
        # 3. 前端传入的值优先
        if model_config.get("apiKey"):
            full_config["apiKey"] = model_config["apiKey"]
        if model_config.get("endpoint"):
            full_config["endpoint"] = model_config["endpoint"]
        if model_config.get("model"):
            full_config["model"] = model_config["model"]
        
        # 4. 验证必要字段
        if not full_config.get("apiKey"):
            logger.warning(f"No API key found for provider: {provider}")
        if not full_config.get("endpoint"):
            logger.warning(f"No endpoint found for provider: {provider}")
        
        return full_config

# 全局单例
_config_manager = None

def get_llm_config_manager() -> LLMConfigManager:
    """获取全局LLM配置管理器"""
    global _config_manager
    if _config_manager is None:
        _config_manager = LLMConfigManager()
    return _config_manager
