"""评测输入与输出的数据模型。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class EvalCase:
    """一条可复跑的评测用例。"""

    case_id: str
    category: str
    query: str
    tags: list[str] = field(default_factory=list)
    expected: dict[str, Any] = field(default_factory=dict)
    source_case_id: str | None = None
    repeat_index: int | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "EvalCase":
        return cls(
            case_id=str(payload["case_id"]),
            category=str(payload["category"]),
            query=str(payload["query"]),
            tags=[str(tag) for tag in payload.get("tags", [])],
            expected=dict(payload.get("expected") or {}),
            source_case_id=(str(payload["source_case_id"]) if payload.get("source_case_id") else None),
            repeat_index=(int(payload["repeat_index"]) if payload.get("repeat_index") is not None else None),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MetricScore:
    """单个评分器的标准结果。"""

    score: float
    numerator: float
    denominator: float
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ScoredCase:
    """一条用例的聚合评分。"""

    case_id: str
    category: str
    quality_score: float
    gate_passed: bool
    metrics: dict[str, dict[str, Any]]
    hard_gate_failures: list[str] = field(default_factory=list)
    runtime: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
