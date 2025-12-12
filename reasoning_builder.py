"""
推理参数构建器
根据配置类型生成对应的 API 参数

各模型类型的参数格式参考 cherry-studio 实现:
- DeepSeek: {"thinking": {"type": "enabled"}}
- OpenAI: {"reasoning_effort": "medium"}
- Anthropic: {"thinking": {"type": "enabled", "budget_tokens": 16000}}
- Gemini: {"thinkingConfig": {"includeThoughts": true, "thinkingBudget": 8192}}
- Qwen: {"enable_thinking": true, "thinking_budget": 8192}
- OpenRouter: {"reasoning": {"enabled": true, "effort": "medium"}}
"""

from typing import Dict, Any
from reasoning_config import (
    ReasoningConfig,
    ReasoningType,
    ReasoningEffort,
    EFFORT_RATIO,
)


class ReasoningParamsBuilder:
    """推理参数构建器"""

    def __init__(self, config: ReasoningConfig):
        self.config = config

    def build(self) -> Dict[str, Any]:
        """根据配置类型构建参数"""
        if not self.config.enabled:
            return {}

        builders = {
            ReasoningType.DEEPSEEK: self._build_deepseek,
            ReasoningType.OPENAI: self._build_openai,
            ReasoningType.ANTHROPIC: self._build_anthropic,
            ReasoningType.GEMINI: self._build_gemini,
            ReasoningType.QWEN: self._build_qwen,
            ReasoningType.OPENROUTER: self._build_openrouter,
            ReasoningType.CUSTOM: self._build_custom,
            ReasoningType.DISABLED: lambda: {},
        }

        builder = builders.get(self.config.reasoning_type)
        if builder:
            params = builder()
            # 合并自定义参数 (自定义参数优先级最高)
            if self.config.custom_params:
                params = self._deep_merge(params, self.config.custom_params)
            return params
        return {}

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """深度合并两个字典"""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _build_deepseek(self) -> Dict[str, Any]:
        """
        DeepSeek R1/V3.1 参数格式
        参考: https://api-docs.deepseek.com/
        """
        if self.config.effort == ReasoningEffort.NONE:
            return {"thinking": {"type": "disabled"}}
        return {"thinking": {"type": "enabled"}}

    def _build_openai(self) -> Dict[str, Any]:
        """
        OpenAI o1/o3/GPT-5 参数格式
        参考: https://platform.openai.com/docs/guides/reasoning
        """
        effort = self.config.effort.value
        # OpenAI 不支持 auto，转换为 medium
        if effort == "auto":
            effort = "medium"
        # OpenAI 不支持 minimal，转换为 low
        if effort == "minimal":
            effort = "low"
        return {"reasoning_effort": effort}

    def _build_anthropic(self) -> Dict[str, Any]:
        """
        Anthropic Claude 3.7/4 参数格式
        参考: https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking
        """
        if self.config.effort == ReasoningEffort.NONE:
            return {"thinking": {"type": "disabled"}}

        params: Dict[str, Any] = {"thinking": {"type": "enabled"}}

        # 设置 budget_tokens
        if self.config.budget_tokens:
            params["thinking"]["budget_tokens"] = self.config.budget_tokens
        else:
            # 根据 effort 计算默认预算 (基于 16K 基准)
            base_tokens = 16000
            ratio = EFFORT_RATIO.get(self.config.effort, 0.5)
            if ratio <= 1:
                params["thinking"]["budget_tokens"] = int(base_tokens * ratio)
            else:
                params["thinking"]["budget_tokens"] = base_tokens

        return params

    def _build_gemini(self) -> Dict[str, Any]:
        """
        Google Gemini 2.5+ 参数格式
        参考: https://ai.google.dev/gemini-api/docs/thinking
        """
        if self.config.effort == ReasoningEffort.NONE:
            return {
                "thinkingConfig": {
                    "includeThoughts": False,
                    "thinkingBudget": 0,
                }
            }

        params: Dict[str, Any] = {
            "thinkingConfig": {
                "includeThoughts": True,
            }
        }

        if self.config.budget_tokens:
            params["thinkingConfig"]["thinkingBudget"] = self.config.budget_tokens
        elif self.config.effort == ReasoningEffort.AUTO:
            params["thinkingConfig"]["thinkingBudget"] = -1  # -1 表示自动
        else:
            # 根据 effort 计算默认预算 (基于 24K 基准)
            base_tokens = 24000
            ratio = EFFORT_RATIO.get(self.config.effort, 0.5)
            if ratio <= 1:
                params["thinkingConfig"]["thinkingBudget"] = int(base_tokens * ratio)

        return params

    def _build_qwen(self) -> Dict[str, Any]:
        """
        Qwen3 参数格式
        参考: https://help.aliyun.com/zh/model-studio/developer-reference/qwen-api
        """
        if self.config.effort == ReasoningEffort.NONE:
            return {"enable_thinking": False}

        params: Dict[str, Any] = {"enable_thinking": True}

        if self.config.budget_tokens:
            params["thinking_budget"] = self.config.budget_tokens
        else:
            # 根据 effort 计算默认预算 (基于 38K 基准)
            base_tokens = 38912
            ratio = EFFORT_RATIO.get(self.config.effort, 0.5)
            if ratio <= 1:
                params["thinking_budget"] = int(base_tokens * ratio)

        return params

    def _build_openrouter(self) -> Dict[str, Any]:
        """
        OpenRouter 统一参数格式
        参考: https://openrouter.ai/docs/parameters
        """
        if self.config.effort == ReasoningEffort.NONE:
            return {
                "reasoning": {
                    "enabled": False,
                    "exclude": True,
                }
            }

        effort = self.config.effort.value
        # OpenRouter 不支持 auto/minimal，转换为 medium/low
        if effort == "auto":
            effort = "medium"
        if effort == "minimal":
            effort = "low"

        return {
            "reasoning": {
                "enabled": True,
                "effort": effort,
            }
        }

    def _build_custom(self) -> Dict[str, Any]:
        """
        自定义参数 (直接使用 custom_params)
        """
        return {}


def build_reasoning_params(config: ReasoningConfig) -> Dict[str, Any]:
    """便捷函数：根据配置构建推理参数"""
    builder = ReasoningParamsBuilder(config)
    return builder.build()
