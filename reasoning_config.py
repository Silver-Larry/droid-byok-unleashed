"""
推理模型参数配置模块
定义不同模型类型的参数格式和配置加载逻辑

支持的推理类型:
- deepseek: DeepSeek R1/V3.1 系列
- openai: OpenAI o1/o3/GPT-5 系列
- anthropic: Claude 3.7/4 系列
- gemini: Gemini 2.5+ 系列
- qwen: Qwen3 系列
- openrouter: OpenRouter 统一格式
- custom: 自定义参数
"""

import os
import json
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum


class ReasoningType(Enum):
    """推理模型类型枚举"""
    DEEPSEEK = "deepseek"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    QWEN = "qwen"
    OPENROUTER = "openrouter"
    CUSTOM = "custom"
    DISABLED = "disabled"


class ReasoningEffort(Enum):
    """推理强度枚举"""
    NONE = "none"
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    AUTO = "auto"


# 推理强度到 Token 预算比例的映射 (参考 cherry-studio)
EFFORT_RATIO: Dict[ReasoningEffort, float] = {
    ReasoningEffort.NONE: 0.01,
    ReasoningEffort.MINIMAL: 0.05,
    ReasoningEffort.LOW: 0.05,
    ReasoningEffort.MEDIUM: 0.5,
    ReasoningEffort.HIGH: 0.8,
    ReasoningEffort.AUTO: 2.0,
}

# 各推理类型支持的强度选项
SUPPORTED_EFFORTS: Dict[str, list] = {
    "deepseek": ["none", "auto"],
    "openai": ["low", "medium", "high"],
    "anthropic": ["none", "low", "medium", "high"],
    "gemini": ["none", "low", "medium", "high", "auto"],
    "qwen": ["none", "low", "medium", "high"],
    "openrouter": ["none", "low", "medium", "high"],
    "custom": ["none", "minimal", "low", "medium", "high", "auto"],
}


@dataclass
class ReasoningConfig:
    """推理配置数据类"""
    enabled: bool
    reasoning_type: ReasoningType
    effort: ReasoningEffort
    budget_tokens: Optional[int]
    custom_params: Dict[str, Any]
    filter_thinking_tags: bool

    @classmethod
    def from_env(cls) -> "ReasoningConfig":
        """从环境变量加载配置"""
        enabled = os.getenv("REASONING_ENABLED", "false").lower() == "true"

        type_str = os.getenv("REASONING_TYPE", "deepseek").lower()
        try:
            reasoning_type = ReasoningType(type_str)
        except ValueError:
            reasoning_type = ReasoningType.DEEPSEEK

        effort_str = os.getenv("REASONING_EFFORT", "auto").lower()
        try:
            effort = ReasoningEffort(effort_str)
        except ValueError:
            effort = ReasoningEffort.AUTO

        budget_str = os.getenv("REASONING_BUDGET_TOKENS", "")
        budget_tokens = int(budget_str) if budget_str.isdigit() else None

        custom_params_str = os.getenv("REASONING_CUSTOM_PARAMS", "{}")
        try:
            custom_params = json.loads(custom_params_str)
        except json.JSONDecodeError:
            custom_params = {}

        filter_tags = os.getenv("FILTER_THINKING_TAGS", "true").lower() == "true"

        return cls(
            enabled=enabled,
            reasoning_type=reasoning_type,
            effort=effort,
            budget_tokens=budget_tokens,
            custom_params=custom_params,
            filter_thinking_tags=filter_tags,
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式 (便于 API 返回)"""
        return {
            "enabled": self.enabled,
            "reasoning_type": self.reasoning_type.value,
            "effort": self.effort.value,
            "budget_tokens": self.budget_tokens,
            "custom_params": self.custom_params,
            "filter_thinking_tags": self.filter_thinking_tags,
        }

    def __repr__(self) -> str:
        return (
            f"ReasoningConfig(enabled={self.enabled}, "
            f"type={self.reasoning_type.value}, "
            f"effort={self.effort.value}, "
            f"budget_tokens={self.budget_tokens})"
        )


def get_reasoning_types_info() -> Dict[str, Any]:
    """获取支持的推理类型信息 (供前端使用)"""
    return {
        "types": [
            {
                "value": "deepseek",
                "label": "DeepSeek (R1/V3.1)",
                "description": "使用 thinking.type 参数",
                "supported_efforts": SUPPORTED_EFFORTS["deepseek"],
            },
            {
                "value": "openai",
                "label": "OpenAI (o1/o3/GPT-5)",
                "description": "使用 reasoning_effort 参数",
                "supported_efforts": SUPPORTED_EFFORTS["openai"],
            },
            {
                "value": "anthropic",
                "label": "Anthropic (Claude 3.7/4)",
                "description": "使用 thinking.budgetTokens 参数",
                "supported_efforts": SUPPORTED_EFFORTS["anthropic"],
            },
            {
                "value": "gemini",
                "label": "Google (Gemini 2.5+)",
                "description": "使用 thinkingConfig 参数",
                "supported_efforts": SUPPORTED_EFFORTS["gemini"],
            },
            {
                "value": "qwen",
                "label": "Qwen (Qwen3)",
                "description": "使用 enable_thinking 参数",
                "supported_efforts": SUPPORTED_EFFORTS["qwen"],
            },
            {
                "value": "openrouter",
                "label": "OpenRouter",
                "description": "使用 reasoning.enabled 参数",
                "supported_efforts": SUPPORTED_EFFORTS["openrouter"],
            },
            {
                "value": "custom",
                "label": "自定义",
                "description": "使用自定义 JSON 参数",
                "supported_efforts": SUPPORTED_EFFORTS["custom"],
            },
        ],
        "efforts": [
            {"value": "none", "label": "关闭"},
            {"value": "minimal", "label": "最小"},
            {"value": "low", "label": "低"},
            {"value": "medium", "label": "中"},
            {"value": "high", "label": "高"},
            {"value": "auto", "label": "自动"},
        ],
    }
