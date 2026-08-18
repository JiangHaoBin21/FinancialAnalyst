"""结构化指标的证据支撑评分。"""

from __future__ import annotations

from typing import Any

from evals.models import MetricScore
from evals.scorers.common import (
    extract_evidence_facts,
    fact_matches,
    iter_supporting_metrics,
    metric_score,
    parse_evidence,
)


def score_fact_grounding(state: dict[str, Any]) -> MetricScore:
    """核对 Analysis supporting_metrics 是否能在 evidence 原始工具结果中找到。"""
    analysis = state.get("analysis_result") or {}
    metrics = list(iter_supporting_metrics(analysis.get("dimensions") or []))
    evidence = parse_evidence(analysis.get("evidence"))
    facts = extract_evidence_facts(evidence)
    matched: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []

    for metric in metrics:
        if any(fact_matches(metric, fact) for fact in facts):
            matched.append(metric)
        else:
            unmatched.append(metric)

    denominator = len(metrics) or 1
    return metric_score(
        len(matched),
        denominator,
        metric_count=len(metrics),
        evidence_fact_count=len(facts),
        matched=matched,
        unmatched=unmatched,
        note=(
            "第一迭代只验证结构化 supporting_metrics 与 evidence 的一致性；"
            "不对报告自由文本中的全部事实做实体抽取。"
        ),
    )
