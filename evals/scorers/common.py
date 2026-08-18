"""评分器共享的规范化与计分函数。"""

from __future__ import annotations

import json
import math
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from evals.models import MetricScore


DIMENSION_ALIASES: dict[str, tuple[str, ...]] = {
    "盈利能力": ("盈利", "利润率", "回报"),
    "成长能力": ("成长", "增长"),
    "偿债能力": ("偿债", "债务", "流动性"),
    "现金流质量": ("现金流", "现金转化"),
    "经营质量": ("经营质量", "经营效率", "营运", "周转", "利润质量"),
    "资产质量": ("资产质量", "资产结构", "应收", "存货", "商誉"),
    "风险": ("风险", "压力"),
}


def metric_score(numerator: float, denominator: float, **details: Any) -> MetricScore:
    score = 0.0 if denominator <= 0 else 100.0 * numerator / denominator
    return MetricScore(
        score=round(max(0.0, min(100.0, score)), 2),
        numerator=numerator,
        denominator=denominator,
        details=details,
    )


def normalize_text(value: Any) -> str:
    return re.sub(r"[\s\-_—–，,。；;：:（）()【】\[\]]+", "", str(value or "")).lower()


def text_matches(actual: Any, expected: Any) -> bool:
    left = normalize_text(actual)
    right = normalize_text(expected)
    return bool(left and right and (left in right or right in left))


def normalize_period(value: Any) -> str:
    text = str(value or "").strip()
    digits = re.sub(r"\D", "", text)
    if len(digits) >= 8:
        return digits[:8]
    if len(digits) == 6:
        return digits
    if len(digits) == 4:
        return digits
    return normalize_text(text)


def to_decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip().replace(",", "")
    if not text or text.lower() in {"none", "null", "nan", "--"}:
        return None
    if text.endswith("%"):
        text = text[:-1]
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def values_close(left: Any, right: Any) -> bool:
    left_decimal = to_decimal(left)
    right_decimal = to_decimal(right)
    if left_decimal is None or right_decimal is None:
        return normalize_text(left) == normalize_text(right)
    difference = abs(left_decimal - right_decimal)
    scale = max(abs(left_decimal), abs(right_decimal), Decimal("1"))
    return difference <= max(Decimal("0.01"), scale * Decimal("0.005"))


def normalize_unit(value: Any) -> str:
    unit = normalize_text(value)
    aliases = {
        "%": "percent",
        "百分比": "percent",
        "百分数": "percent",
        "元": "yuan",
        "亿元": "100myuan",
        "万元": "10kyuan",
        "倍": "ratio",
        "ratio": "ratio",
        "无": "none",
        "无单位": "none",
    }
    return aliases.get(unit, unit)


def units_equal(left: Any, right: Any) -> bool:
    return normalize_unit(left) == normalize_unit(right)


def parse_evidence(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return value
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def iter_supporting_metrics(container: Any) -> Iterable[dict[str, Any]]:
    """递归读取结构化结果中的 supporting_metrics。"""
    if isinstance(container, dict):
        metrics = container.get("supporting_metrics")
        if isinstance(metrics, list):
            for metric in metrics:
                if isinstance(metric, dict):
                    yield metric
        for key, value in container.items():
            if key != "supporting_metrics":
                yield from iter_supporting_metrics(value)
    elif isinstance(container, list):
        for item in container:
            yield from iter_supporting_metrics(item)


def extract_evidence_facts(evidence: Any) -> list[dict[str, Any]]:
    """从 evidence tool 的紧凑输出提取指标—期间—值—单位事实。"""
    facts: list[dict[str, Any]] = []

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            name = node.get("name")
            values = node.get("value")
            if name and isinstance(values, list):
                for item in values:
                    if isinstance(item, (list, tuple)) and len(item) >= 2:
                        facts.append(
                            {
                                "name": name,
                                "period": item[0],
                                "value": item[1],
                                "unit": node.get("unit"),
                            }
                        )
                    elif isinstance(item, dict) and "value" in item:
                        facts.append(
                            {
                                "name": name,
                                "period": item.get("period") or item.get("end_date"),
                                "value": item.get("value"),
                                "unit": node.get("unit") or item.get("unit"),
                            }
                        )
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(evidence)
    return facts


def fact_matches(metric: dict[str, Any], fact: dict[str, Any]) -> bool:
    if not text_matches(metric.get("name"), fact.get("name")):
        return False
    if normalize_period(metric.get("period")) != normalize_period(fact.get("period")):
        return False
    if not values_close(metric.get("value"), fact.get("value")):
        return False
    metric_unit = metric.get("unit")
    fact_unit = fact.get("unit")
    return not metric_unit or not fact_unit or units_equal(metric_unit, fact_unit)


def json_safe(value: Any) -> bool:
    try:
        json.dumps(value, ensure_ascii=False, allow_nan=False)
        return True
    except (TypeError, ValueError):
        return False


def finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
