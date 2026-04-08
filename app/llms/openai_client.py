from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from openai import OpenAI

from app.core.config import settings
from app.llms.base import BaseLLMClient


class LLMClientError(Exception):
    """LLM 客户端统一异常"""
    pass


@dataclass
class OpenAIClientConfig:
    """
    OpenAI 客户端配置

    说明：
    - api_key: OpenAI / 兼容 OpenAI API 服务的密钥
    - model: 默认使用的模型名
    - base_url: 可选，自定义兼容 OpenAI 的服务地址
    - timeout: 请求超时时间（秒）
    """
    api_key: str = settings.OPENAI_API_KEY
    model: str = settings.OPENAI_MODEL
    base_url: Optional[str] = getattr(settings, "OPENAI_BASE_URL", None)
    timeout: float = getattr(settings, "OPENAI_TIMEOUT", 60.0)


class OpenAIClient(BaseLLMClient):
    """
    基于 OpenAI SDK 的 LLM Client 实现。

    职责：
    1. 实现 BaseLLMClient 约定的 generate / chat 接口
    2. 屏蔽 OpenAI SDK 调用细节
    3. 为上层 skills / agents 提供统一文本生成能力
    """

    def __init__(self, config: Optional[OpenAIClientConfig] = None):
        self.config = config or OpenAIClientConfig()

        if not self.config.api_key:
            raise ValueError("OpenAI API Key 不能为空")
        if not self.config.model:
            raise ValueError("OpenAI model 不能为空")

        client_kwargs: dict[str, Any] = {
            "api_key": self.config.api_key,
            "timeout": self.config.timeout,
        }
        if self.config.base_url:
            client_kwargs["base_url"] = self.config.base_url

        self.client = OpenAI(**client_kwargs)
        self.model = self.config.model

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """
        单轮文本生成。

        这里内部仍然走 chat completions，只是帮上层把 prompt
        自动包装成单条 user message。
        """
        if not prompt or not prompt.strip():
            raise ValueError("prompt 不能为空")

        messages = [
            {"role": "user", "content": prompt.strip()}
        ]
        return self.chat(messages=messages, **kwargs)

    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """
        多轮对话生成。

        messages 示例：
        [
            {"role": "system", "content": "..."},
            {"role": "user", "content": "..."}
        ]
        """
        if not messages:
            raise ValueError("messages 不能为空")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                **kwargs,
            )
        except Exception as e:
            raise LLMClientError(f"OpenAI 调用失败: {str(e)}") from e

        try:
            content = response.choices[0].message.content
        except Exception as e:
            raise LLMClientError(f"OpenAI 返回结果解析失败: {str(e)}") from e

        if content is None:
            return ""

        return content.strip()