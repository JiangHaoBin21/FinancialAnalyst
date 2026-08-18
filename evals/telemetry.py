"""不改变业务返回值的 LLM 调用观测代理。"""

from __future__ import annotations

from time import perf_counter
from typing import Any


class TimedLLMProxy:
    """记录调用数量、工具调用轮次、延迟和异常。"""

    def __init__(self, wrapped_client: Any, pricing: dict[str, Any] | None = None):
        self.wrapped_client = wrapped_client
        self.calls: list[dict[str, Any]] = []
        self.pricing = dict(pricing or {})

    def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list | None = None,
        **kwargs: Any,
    ) -> Any:
        started = perf_counter()
        record: dict[str, Any] = {
            "with_tools": bool(tools),
            "message_count": len(messages or []),
            "stage": self._infer_stage(messages),
            "success": False,
        }
        try:
            result = self.wrapped_client.generate(messages=messages, tools=tools, **kwargs)
            record["success"] = True
            tool_calls = getattr(result, "tool_calls", None) or []
            record["returned_tool_calls"] = len(tool_calls)
            usage = dict(getattr(self.wrapped_client, "last_usage", None) or {})
            if usage:
                record["usage"] = usage
                estimated_cost = self._estimate_cost(usage)
                if estimated_cost is not None:
                    record["estimated_cost"] = estimated_cost
            return result
        except Exception as exc:
            record["error_type"] = type(exc).__name__
            raise
        finally:
            record["latency_ms"] = round((perf_counter() - started) * 1000, 2)
            self.calls.append(record)

    def reset(self) -> None:
        self.calls.clear()

    def snapshot(self) -> dict[str, Any]:
        usage_records = [
            call["usage"] for call in self.calls if isinstance(call.get("usage"), dict)
        ]
        prompt_tokens = sum(int(usage.get("prompt_tokens") or 0) for usage in usage_records)
        completion_tokens = sum(int(usage.get("completion_tokens") or 0) for usage in usage_records)
        cached_prompt_tokens = sum(int(usage.get("cached_prompt_tokens") or 0) for usage in usage_records)
        reasoning_tokens = sum(int(usage.get("reasoning_tokens") or 0) for usage in usage_records)
        total_tokens = sum(int(usage.get("total_tokens") or 0) for usage in usage_records)
        costs = [call.get("estimated_cost") for call in self.calls]
        cost_available = bool(self.calls) and all(isinstance(cost, (int, float)) for cost in costs)
        stage_usage: dict[str, dict[str, Any]] = {}
        for call in self.calls:
            stage = str(call.get("stage") or "unknown")
            bucket = stage_usage.setdefault(
                stage,
                {"call_count": 0, "latency_ms": 0.0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            )
            bucket["call_count"] += 1
            bucket["latency_ms"] += float(call.get("latency_ms") or 0)
            usage = call.get("usage") or {}
            for name in ("prompt_tokens", "completion_tokens", "total_tokens"):
                bucket[name] += int(usage.get(name) or 0)
        for bucket in stage_usage.values():
            bucket["latency_ms"] = round(bucket["latency_ms"], 2)
        snapshot = {
            "llm_call_count": len(self.calls),
            "llm_tool_round_count": sum(call.get("with_tools", False) for call in self.calls),
            "returned_tool_call_count": sum(call.get("returned_tool_calls", 0) for call in self.calls),
            "llm_latency_ms": round(sum(call.get("latency_ms", 0.0) for call in self.calls), 2),
            "llm_failed_call_count": sum(not call.get("success", False) for call in self.calls),
            "llm_calls": list(self.calls),
            "llm_stage_usage": stage_usage,
            "token_usage_available": len(usage_records) == len(self.calls) and bool(self.calls),
            "usage_covered_call_count": len(usage_records),
            "prompt_tokens": prompt_tokens,
            "cached_prompt_tokens": cached_prompt_tokens,
            "completion_tokens": completion_tokens,
            "reasoning_tokens": reasoning_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_available": cost_available,
            "pricing_currency": self.pricing.get("currency"),
        }
        if cost_available:
            snapshot["estimated_cost"] = round(sum(float(cost) for cost in costs), 8)
        else:
            snapshot["estimated_cost"] = None
            snapshot["cost_note"] = (
                "真实 Token 已记录；成本单价未完整配置，未生成估算成本。"
                if usage_records
                else "provider usage 不可用，且未生成估算成本。"
            )
        return snapshot

    @staticmethod
    def _infer_stage(messages: list[dict[str, Any]] | None) -> str:
        system_text = "\n".join(
            str(message.get("content") or "")
            for message in messages or []
            if message.get("role") == "system"
        )
        markers = (
            ("ReflectionAgent，负责", "reflection"),
            ("SupervisorAgent", "supervisor"),
            ("ReportAgent", "report"),
            ("DataAgent", "data"),
            ("AnalysisAgent", "analysis"),
        )
        for marker, stage in markers:
            if marker in system_text:
                return stage
        return "unknown"

    def _estimate_cost(self, usage: dict[str, Any]) -> float | None:
        """按每百万 Token 单价估算成本；配置不完整时不猜测。"""
        input_rate = self.pricing.get("input_per_million_tokens")
        cached_rate = self.pricing.get("cached_input_per_million_tokens")
        output_rate = self.pricing.get("output_per_million_tokens")
        if not isinstance(input_rate, (int, float)) or not isinstance(output_rate, (int, float)):
            return None
        if not isinstance(cached_rate, (int, float)):
            cached_rate = input_rate
        prompt = int(usage.get("prompt_tokens") or 0)
        cached = min(prompt, int(usage.get("cached_prompt_tokens") or 0))
        completion = int(usage.get("completion_tokens") or 0)
        cost = (
            (prompt - cached) * float(input_rate)
            + cached * float(cached_rate)
            + completion * float(output_rate)
        ) / 1_000_000
        return round(cost, 8)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.wrapped_client, name)
