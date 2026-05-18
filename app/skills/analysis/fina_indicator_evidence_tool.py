from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from app.skills.analysis.metric_groups import FINA_INDICATOR_GROUPS
from app.skills.analysis.metric_registry import FINA_INDICATOR_METRIC_REGISTRY


# =========================
# 1. 基础工具函数
# =========================

def to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None

    if isinstance(value, Decimal):
        return value

    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def get_field(record: Any, field_name: str) -> Decimal | None:
    """
    同时兼容 SQLAlchemy ORM 对象和 dict。
    """
    if isinstance(record, dict):
        return to_decimal(record.get(field_name))

    return to_decimal(getattr(record, field_name, None))


def get_period(record: Any) -> str:
    """
    统一取报告期 end_date。
    """
    if isinstance(record, dict):
        end_date = record.get("end_date")
    else:
        end_date = getattr(record, "end_date", None)

    if end_date is None:
        return ""

    if hasattr(end_date, "isoformat"):
        return end_date.isoformat()

    return str(end_date)


# =========================
# 2. 输出压缩
# =========================

AMOUNT_SCALE = Decimal("100000000")
AMOUNT_UNIT = "亿元"


def format_metric_value(value: Decimal | None, unit: str) -> float | None:
    """
    FinaIndicator 字段已经是 TuShare 计算后的结果。

    格式化规则：
    - amount：金额类，转为亿元，保留 2 位小数；
    - %：百分比类，保留 2 位小数，不再除以 100；
    - ratio / 次 / 元/股：保留 4 位小数；
    - None：直接返回 None。
    """
    if value is None:
        return None

    if unit == "amount":
        return float(round(value / AMOUNT_SCALE, 2))

    if unit == "%":
        return float(round(value, 2))

    return float(round(value, 4))


def output_unit(unit: str) -> str:
    if unit == "amount":
        return AMOUNT_UNIT
    return unit


# =========================
# 3. 核心 evidence tool
# =========================

def build_fina_indicator_evidence(
    records: list[Any],
    metric_groups: list[str],
) -> dict[str, Any]:
    """
    FinaIndicator evidence tool 核心函数。

    输入：
    - records: 从 LangGraph state 里取出的 FinaIndicator ORM 列表
    - metric_groups: ReAct Agent 指定的 group 列表

    输出：
    - 只输出 name、unit、value
    - 不输出 formula、description、depends_on
    - value 使用 [["YYYY-MM-DD", value], ...] 的紧凑结构

    注意：
    - FinaIndicator 不做复杂计算；
    - 只根据 registry_item["field_name"] 从 ORM 里直接取值；
    - 这张表定位为“标准指标摘要层”。
    """

    if not records:
        return {"fina_indicator": []}

    selected_groups = [
        group for group in metric_groups
        if group in FINA_INDICATOR_GROUPS
    ]

    if not selected_groups:
        return {"fina_indicator": []}

    sorted_records = sorted(
        records,
        key=lambda r: get_period(r),
    )

    result = []

    for group_code in selected_groups:
        group_config = FINA_INDICATOR_GROUPS[group_code]
        metric_codes = group_config["metrics"]

        group_metrics = []

        for metric_code in metric_codes:
            registry_item = FINA_INDICATOR_METRIC_REGISTRY.get(metric_code)

            if registry_item is None:
                continue

            field_name = registry_item.get("field_name")
            if not field_name:
                continue

            unit = registry_item["unit"]

            values = []
            for record in sorted_records:
                period = get_period(record)
                raw_value = get_field(record, field_name)
                formatted_value = format_metric_value(raw_value, unit)

                values.append([period, formatted_value])

            group_metrics.append(
                {
                    "name": registry_item["name"],
                    "unit": output_unit(unit),
                    "value": values,
                }
            )

        result.append(
            {
                "group": group_code,
                "metrics": group_metrics,
            }
        )

    return {"fina_indicator": result}


# =========================
# 4. ReAct runtime wrapper 可选
# =========================

class FinaIndicatorEvidenceRuntimeTool:
    """
    给 ReAct Agent 使用的轻量包装。

    注意：
    - records 不由 LLM 传入；
    - records 应该来自 LangGraph state；
    - LLM 只需要选择 metric_groups。
    """

    def __init__(self, records: list[Any]):
        self.records = records

    def run(self, metric_groups: list[str]) -> dict[str, Any]:
        return build_fina_indicator_evidence(
            records=self.records,
            metric_groups=metric_groups,
        )