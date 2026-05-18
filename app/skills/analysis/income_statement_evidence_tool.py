from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Callable

from app.skills.analysis.metric_groups import INCOME_GROUPS
from app.skills.analysis.metric_registry import INCOME_METRIC_REGISTRY


# =========================
# 1. 基础安全计算函数
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


def safe_add(*values: Any) -> Decimal | None:
    total = Decimal("0")
    has_value = False

    for value in values:
        decimal_value = to_decimal(value)
        if decimal_value is not None:
            total += decimal_value
            has_value = True

    return total if has_value else None


def safe_sub(a: Any, b: Any) -> Decimal | None:
    a = to_decimal(a)
    b = to_decimal(b)

    if a is None or b is None:
        return None

    return a - b


def safe_div(numerator: Any, denominator: Any) -> Decimal | None:
    numerator = to_decimal(numerator)
    denominator = to_decimal(denominator)

    if numerator is None or denominator is None or denominator == 0:
        return None

    return numerator / denominator


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
# 2. 单期上下文构造
# =========================

def build_income_context(record: Any) -> dict[str, Decimal | None]:
    """
    把一条 Income ORM record 转成当前期间的计算上下文。

    注意：
    - 这里不会直接返回给 LLM；
    - 只是 tool 内部计算用；
    - ctx 里既有原始字段，也有中间派生字段。
    """

    ctx: dict[str, Decimal | None] = {
        # 收入与利润层级
        "total_revenue": get_field(record, "total_revenue"),
        "revenue": get_field(record, "revenue"),
        "operate_profit": get_field(record, "operate_profit"),
        "total_profit": get_field(record, "total_profit"),
        "n_income": get_field(record, "n_income"),
        "n_income_attr_p": get_field(record, "n_income_attr_p"),
        "minority_gain": get_field(record, "minority_gain"),

        # 成本费用
        "oper_cost": get_field(record, "oper_cost"),
        "total_cogs": get_field(record, "total_cogs"),
        "sell_exp": get_field(record, "sell_exp"),
        "admin_exp": get_field(record, "admin_exp"),
        "biz_tax_surchg": get_field(record, "biz_tax_surchg"),

        # 研发与财务费用拆解
        "rd_exp": get_field(record, "rd_exp"),
        "fin_exp": get_field(record, "fin_exp"),
        "fin_exp_int_exp": get_field(record, "fin_exp_int_exp"),
        "fin_exp_int_inc": get_field(record, "fin_exp_int_inc"),

        # 非主营损益
        "invest_income": get_field(record, "invest_income"),
        "fv_value_chg_gain": get_field(record, "fv_value_chg_gain"),
        "oth_income": get_field(record, "oth_income"),
        "asset_disp_income": get_field(record, "asset_disp_income"),
        "non_oper_income": get_field(record, "non_oper_income"),
        "non_oper_exp": get_field(record, "non_oper_exp"),

        # 减值损失
        "assets_impair_loss": get_field(record, "assets_impair_loss"),
        "credit_impa_loss": get_field(record, "credit_impa_loss"),
        "oth_impair_loss_assets": get_field(record, "oth_impair_loss_assets"),

        # 综合收益
        "oth_compr_income": get_field(record, "oth_compr_income"),
        "compr_inc_attr_p": get_field(record, "compr_inc_attr_p"),
    }

    # =========================
    # 中间派生变量
    # =========================

    ctx["net_interest_expense"] = safe_sub(
        ctx["fin_exp_int_exp"],
        ctx["fin_exp_int_inc"],
    )

    ctx["net_non_operating_income"] = safe_sub(
        ctx["non_oper_income"],
        ctx["non_oper_exp"],
    )

    ctx["non_core_profit_total"] = safe_add(
        ctx["invest_income"],
        ctx["fv_value_chg_gain"],
        ctx["oth_income"],
        ctx["asset_disp_income"],
        ctx["net_non_operating_income"],
    )

    ctx["total_impairment_loss"] = safe_add(
        ctx["assets_impair_loss"],
        ctx["credit_impa_loss"],
        ctx["oth_impair_loss_assets"],
    )

    ctx["comprehensive_income_gap"] = safe_sub(
        ctx["compr_inc_attr_p"],
        ctx["n_income_attr_p"],
    )

    return ctx


# =========================
# 3. 指标计算函数
# =========================

MetricCalculator = Callable[[dict[str, Decimal | None]], Decimal | None]


INCOME_METRIC_CALCULATORS: dict[str, MetricCalculator] = {
    # =========================================================
    # 1. 收入与利润层级 profit_scale_layers
    # =========================================================
    "total_revenue_amount": lambda c: c["total_revenue"],
    "revenue_amount": lambda c: c["revenue"],
    "operating_profit_amount": lambda c: c["operate_profit"],
    "total_profit_amount": lambda c: c["total_profit"],
    "net_income_amount": lambda c: c["n_income"],

    # =========================================================
    # 2. 成本与期间费用金额 cost_expense_amounts
    # =========================================================
    "operating_cost_amount": lambda c: c["oper_cost"],
    "total_cogs_amount": lambda c: c["total_cogs"],
    "selling_expense_amount": lambda c: c["sell_exp"],
    "admin_expense_amount": lambda c: c["admin_exp"],
    "tax_surcharge_amount": lambda c: c["biz_tax_surchg"],

    # =========================================================
    # 3. 研发投入与财务费用拆解 rd_and_finance_detail
    # =========================================================
    "rd_expense_amount": lambda c: c["rd_exp"],
    "finance_expense_amount": lambda c: c["fin_exp"],
    "interest_expense_amount": lambda c: c["fin_exp_int_exp"],
    "interest_income_amount": lambda c: c["fin_exp_int_inc"],
    "net_interest_expense_amount": lambda c: c["net_interest_expense"],

    # =========================================================
    # 4. 非主营损益与一次性收益 non_core_profit_sources
    # =========================================================
    "investment_income_amount": lambda c: c["invest_income"],
    "fair_value_change_gain_amount": lambda c: c["fv_value_chg_gain"],
    "other_income_amount": lambda c: c["oth_income"],
    "asset_disposal_income_amount": lambda c: c["asset_disp_income"],
    "net_non_operating_income_amount": lambda c: c["net_non_operating_income"],
    "non_core_profit_total_amount": lambda c: c["non_core_profit_total"],
    "non_core_profit_to_total_profit": lambda c: safe_div(
        c["non_core_profit_total"],
        c["total_profit"],
    ),

    # =========================================================
    # 5. 减值损失 impairment_losses
    # =========================================================
    "asset_impairment_loss_amount": lambda c: c["assets_impair_loss"],
    "credit_impairment_loss_amount": lambda c: c["credit_impa_loss"],
    "other_asset_impairment_loss_amount": lambda c: c["oth_impair_loss_assets"],
    "total_impairment_loss_amount": lambda c: c["total_impairment_loss"],
    "impairment_to_operating_profit": lambda c: safe_div(
        c["total_impairment_loss"],
        c["operate_profit"],
    ),

    # =========================================================
    # 6. 归母与少数股东损益 profit_attribution
    # =========================================================
    "parent_net_income_amount": lambda c: c["n_income_attr_p"],
    "minority_gain_amount": lambda c: c["minority_gain"],
    "parent_net_income_share": lambda c: safe_div(
        c["n_income_attr_p"],
        c["n_income"],
    ),
    "minority_gain_share": lambda c: safe_div(
        c["minority_gain"],
        c["n_income"],
    ),

    # =========================================================
    # 7. 其他综合收益与综合收益 comprehensive_income
    # =========================================================
    "other_comprehensive_income_amount": lambda c: c["oth_compr_income"],
    "parent_comprehensive_income_amount": lambda c: c["compr_inc_attr_p"],
    "comprehensive_income_gap_amount": lambda c: c["comprehensive_income_gap"],
    "comprehensive_income_gap_to_parent_net_income": lambda c: safe_div(
        c["comprehensive_income_gap"],
        c["n_income_attr_p"],
    ),
}


# =========================
# 4. 输出压缩
# =========================

AMOUNT_SCALE = Decimal("100000000")
AMOUNT_UNIT = "亿元"


def format_metric_value(value: Decimal | None, unit: str) -> float | None:
    """
    为了节省上下文：
    - amount 默认转为亿元，保留 2 位小数；
    - ratio 保留 4 位小数；
    - None 直接返回 None。
    """
    if value is None:
        return None

    if unit == "amount":
        return float(round(value / AMOUNT_SCALE, 2))

    if unit == "ratio":
        return float(round(value, 4))

    return float(round(value, 4))


def output_unit(unit: str) -> str:
    if unit == "amount":
        return AMOUNT_UNIT
    return unit


# =========================
# 5. 核心 evidence tool
# =========================

def build_income_evidence(
    records: list[Any],
    metric_groups: list[str],
) -> dict[str, Any]:
    """
    Income evidence tool 核心函数。

    输入：
    - records: 从 LangGraph state 里取出的 Income ORM 列表
    - metric_groups: ReAct Agent 指定的 group 列表

    输出：
    - 只输出 name、unit、value
    - 不输出 formula、description、depends_on
    - value 使用 [["YYYY-MM-DD", value], ...] 的紧凑结构
    """

    if not records:
        return {"income": []}

    selected_groups = [
        group for group in metric_groups
        if group in INCOME_GROUPS
    ]

    if not selected_groups:
        return {"income": []}

    sorted_records = sorted(
        records,
        key=lambda r: get_period(r),
    )

    contexts = [
        {
            "period": get_period(record),
            "ctx": build_income_context(record),
        }
        for record in sorted_records
    ]

    result = []

    for group_code in selected_groups:
        group_config = INCOME_GROUPS[group_code]
        metric_codes = group_config["metrics"]

        group_metrics = []

        for metric_code in metric_codes:
            registry_item = INCOME_METRIC_REGISTRY.get(metric_code)
            calculator = INCOME_METRIC_CALCULATORS.get(metric_code)

            if registry_item is None or calculator is None:
                continue

            unit = registry_item["unit"]

            values = []

            for item in contexts:
                period = item["period"]
                ctx = item["ctx"]

                raw_value = calculator(ctx)
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

    return {"income": result}


# =========================
# 6. ReAct runtime wrapper 可选
# =========================

class IncomeEvidenceRuntimeTool:
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
        return build_income_evidence(
            records=self.records,
            metric_groups=metric_groups,
        )