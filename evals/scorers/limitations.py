"""数据限制的语义类型识别与覆盖率计算。"""

from __future__ import annotations

from typing import Any

from evals.scorers.common import normalize_text


LIMITATION_PATTERNS: dict[str, tuple[str, ...]] = {
    "missing_peer_benchmark": ("行业对比", "同业对比", "同行对比", "可比公司", "横向比较"),
    "missing_or_incomplete_period": ("数据缺失", "数据不完整", "期间缺失", "季度缺失", "报告期缺失"),
    "outside_financial_scope": ("估值", "股价", "实时行情", "技术面", "市场交易"),
    "missing_external_context": ("宏观", "行业景气", "市场环境", "政策", "竞争格局"),
    "forecast_uncertainty": ("预测", "未来", "前瞻", "盈利预期", "业绩预期"),
    "accounting_disclosure_limit": ("会计", "披露", "审计", "口径", "附注"),
}


def classify_limitations(items: Any) -> set[str]:
    """将自由文本限制归并为可稳定比较的语义类型。"""
    if not isinstance(items, list):
        return set()
    categories: set[str] = set()
    for item in items:
        normalized = normalize_text(item)
        if not normalized:
            continue
        matched = False
        for category, patterns in LIMITATION_PATTERNS.items():
            if any(normalize_text(pattern) in normalized for pattern in patterns):
                categories.add(category)
                matched = True
        if not matched:
            categories.add(f"other:{normalized}")
    return categories
