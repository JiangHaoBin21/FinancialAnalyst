"""定义大模型统一抽象接口"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseLLMClient(ABC):
    """
    项目内所有大模型客户端的统一抽象接口。

    设计目的：
    1. 解耦上层 skills / agents 与具体模型厂商 SDK
    2. 统一模型调用方式
    3. 方便后续扩展 OpenAI / DeepSeek / Mock 等不同实现
    """

    @abstractmethod
    def generate(self, messages: list[dict[str, str]], tools: list = None, **kwargs: Any) -> str:
        """
        单轮文本生成。
        """
        raise NotImplementedError

    @abstractmethod
    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """
        多轮对话生成。
        """
        raise NotImplementedError