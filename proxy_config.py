"""
代理服务配置管理模块
支持从环境变量和配置文件加载配置，并提供持久化功能
"""

import os
import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional, Dict, Any

CONFIG_FILE = Path(__file__).parent / "proxy_config.json"


# Supported API format types
API_FORMAT_TYPES = ["openai", "openai-response", "anthropic", "gemini", "azure-openai"]


@dataclass
class ProxyConfig:
    """代理服务配置"""
    proxy_port: int = 5000
    proxy_api_key: str = ""  # 本地代理的 API Key（可选）
    upstream_api_key: str = ""
    upstream_base_url: str = "https://api.deepseek.com"
    upstream_api_format: str = "openai"  # API format type

    @classmethod
    def load(cls) -> "ProxyConfig":
        """
        从环境变量和配置文件加载配置
        优先级：环境变量 > 配置文件 > 默认值
        """
        config = cls()

        # 1. 先从配置文件加载
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for key, value in data.items():
                        if hasattr(config, key):
                            setattr(config, key, value)
            except (json.JSONDecodeError, IOError) as e:
                print(f"[WARNING] Failed to load config file: {e}")

        # 2. 环境变量覆盖配置文件
        if os.getenv("PROXY_PORT"):
            try:
                config.proxy_port = int(os.getenv("PROXY_PORT"))
            except ValueError:
                pass
        if os.getenv("PROXY_API_KEY"):
            config.proxy_api_key = os.getenv("PROXY_API_KEY")
        if os.getenv("UPSTREAM_API_KEY"):
            config.upstream_api_key = os.getenv("UPSTREAM_API_KEY")
        if os.getenv("UPSTREAM_BASE_URL"):
            config.upstream_base_url = os.getenv("UPSTREAM_BASE_URL")

        return config

    def save(self) -> bool:
        """
        保存配置到文件
        返回是否保存成功
        """
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            print(f"[ERROR] Failed to save config file: {e}")
            return False

    def to_dict(self, hide_secrets: bool = True) -> Dict[str, Any]:
        """
        转换为字典格式
        
        Args:
            hide_secrets: 是否隐藏敏感信息（API Key 只显示后 4 位）
        """
        data = asdict(self)
        if hide_secrets:
            data["proxy_api_key"] = self._mask_key(data["proxy_api_key"])
            data["upstream_api_key"] = self._mask_key(data["upstream_api_key"])
        return data

    @staticmethod
    def _mask_key(key: str) -> str:
        """隐藏 API Key，只显示后 4 位"""
        if not key:
            return ""
        if len(key) <= 4:
            return "****"
        return "***" + key[-4:]

    def validate_port(self, port: int) -> bool:
        """验证端口号是否有效"""
        return 1 <= port <= 65535

    def update(self, **kwargs) -> Dict[str, Any]:
        """
        更新配置
        
        Returns:
            包含更新结果的字典：
            - success: 是否成功
            - restart_required: 是否需要重启
            - error: 错误信息（如果有）
        """
        restart_required = False
        
        # 验证端口
        if "proxy_port" in kwargs:
            port = kwargs["proxy_port"]
            if isinstance(port, str):
                try:
                    port = int(port)
                except ValueError:
                    return {"success": False, "error": "Invalid port number"}
            
            if not self.validate_port(port):
                return {"success": False, "error": "Port must be between 1 and 65535"}
            
            if port != self.proxy_port:
                self.proxy_port = port
                restart_required = True

        # 更新其他配置
        if "proxy_api_key" in kwargs:
            self.proxy_api_key = kwargs["proxy_api_key"]
        if "upstream_api_key" in kwargs:
            self.upstream_api_key = kwargs["upstream_api_key"]
        if "upstream_base_url" in kwargs:
            self.upstream_base_url = kwargs["upstream_base_url"]
        if "upstream_api_format" in kwargs:
            api_format = kwargs["upstream_api_format"]
            if api_format in API_FORMAT_TYPES:
                self.upstream_api_format = api_format

        # 保存到文件
        if not self.save():
            return {"success": False, "error": "Failed to save config file"}

        return {
            "success": True,
            "restart_required": restart_required,
            "config": self.to_dict(hide_secrets=True)
        }


def get_proxy_confi() -> Dict[str, Any]:
    """获取代理配置的元信息（供前端使用）"""
    return {
        "fields": [
            {
                "name": "proxy_port",
                "label": "Proxy Port",
                "type": "number",
                "description": "Local proxy listening port",
                "min": 1,
                "max": 65535,
                "default": 5000,
            },
            {
                "name": "proxy_api_key",
                "label": "Proxy API Key",
                "type": "password",
                "description": "API key for local proxy authentication (optional)",
                "default": "",
            },
            {
                "name": "upstream_api_key",
                "label": "Upstream API Key",
                "type": "password",
                "description": "API key for upstream service",
                "default": "",
            },
            {
                "name": "upstream_base_url",
                "label": "Upstream Base URL",
                "type": "text",
                "description": "Base URL for upstream API service",
                "default": "https://api.deepseek.com",
            },
            {
                "name": "upstream_api_format",
                "label": "API Format",
                "type": "select",
                "description": "API format type for upstream service",
                "default": "openai",
                "options": [
                    {"value": "openai", "label": "OpenAI"},
                    {"value": "openai-response", "label": "OpenAI Response API"},
                    {"value": "anthropic", "label": "Anthropic"},
                    {"value": "gemini", "label": "Google (Gemini)"},
                    {"value": "azure-openai", "label": "Azure OpenAI"},
                ],
            },
        ]
    }
