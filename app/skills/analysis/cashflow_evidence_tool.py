from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Callable

from app.skills.analysis.metric_groups import CASHFLOW_GROUPS
from app.skills.analysis.metric_registry import CASHFLOW_METRIC_REGISTRY


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

def build_cashflow_context(record: Any) -> dict[str, Decimal | None]:
    """
    把一条 CashFlow ORM record 转成当前期间的计算上下文。

    注意：
    - ctx 只在 tool 内部使用；
    - 不会直接返回给 LLM；
    - ctx 里既有原始字段，也有中间派生字段。
    """

    ctx: dict[str, Decimal | None] = {
        # =========================
        # 经营现金流入
        # =========================
        "c_fr_sale_sg": get_field(record, "c_fr_sale_sg"),
        "c_fr_oth_operate_a": get_field(record, "c_fr_oth_operate_a"),
        "c_inf_fr_operate_a": get_field(record, "c_inf_fr_operate_a"),

        # =========================
        # 经营现金流出
        # =========================
        "c_paid_goods_s": get_field(record, "c_paid_goods_s"),
        "c_paid_to_for_empl": get_field(record, "c_paid_to_for_empl"),
        "c_paid_for_taxes": get_field(record, "c_paid_for_taxes"),
        "st_cash_out_act": get_field(record, "st_cash_out_act"),

        # =========================
        # 经营现金流净额
        # =========================
        "n_cashflow_act": get_field(record, "n_cashflow_act"),

        # =========================
        # 投资现金流与资本开支
        # =========================
        "stot_inflows_inv_act": get_field(record, "stot_inflows_inv_act"),
        "c_pay_acq_const_fiolta": get_field(record, "c_pay_acq_const_fiolta"),
        "c_paid_invest": get_field(record, "c_paid_invest"),
        "stot_out_inv_act": get_field(record, "stot_out_inv_act"),
        "n_cashflow_inv_act": get_field(record, "n_cashflow_inv_act"),

        # =========================
        # 筹资现金流
        # =========================
        "c_recp_cap_contrib": get_field(record, "c_recp_cap_contrib"),
        "c_recp_borrow": get_field(record, "c_recp_borrow"),
        "proc_issue_bonds": get_field(record, "proc_issue_bonds"),
        "stot_cash_in_fnc_act": get_field(record, "stot_cash_in_fnc_act"),
        "c_prepay_amt_borr": get_field(record, "c_prepay_amt_borr"),
        "c_pay_dist_dpcp_int_exp": get_field(record, "c_pay_dist_dpcp_int_exp"),
        "stot_cashout_fnc_act": get_field(record, "stot_cashout_fnc_act"),
        "n_cash_flows_fnc_act": get_field(record, "n_cash_flows_fnc_act"),

        # =========================
        # 现金及现金等价物
        # =========================
        "c_cash_equ_beg_period": get_field(record, "c_cash_equ_beg_period"),
        "c_cash_equ_end_period": get_field(record, "c_cash_equ_end_period"),
        "n_incr_cash_cash_equ": get_field(record, "n_incr_cash_cash_equ"),

        # =========================
        # 间接法调节
        # =========================
        "net_profit": get_field(record, "net_profit"),
        "depr_fa_coga_dpba": get_field(record, "depr_fa_coga_dpba"),
        "amort_intang_assets": get_field(record, "amort_intang_assets"),
        "decr_inventories": get_field(record, "decr_inventories"),
        "decr_oper_payable": get_field(record, "decr_oper_payable"),
        "incr_oper_payable": get_field(record, "incr_oper_payable"),
        "im_net_cashflow_oper_act": get_field(record, "im_net_cashflow_oper_act"),
    }

    # =========================
    # 中间派生变量
    # =========================

    # 债务融资收到的现金 = 取得借款收到的现金 + 发行债券收到的现金
    ctx["debt_financing_cash_received"] = safe_add(
        ctx["c_recp_borrow"],
        ctx["proc_issue_bonds"],
    )

    # 折旧摊销合计 = 固定资产折旧等 + 无形资产摊销
    ctx["depreciation_amortization_amount"] = safe_add(
        ctx["depr_fa_coga_dpba"],
        ctx["amort_intang_assets"],
    )

    return ctx


# =========================
# 3. 指标计算函数
# =========================

MetricCalculator = Callable[[dict[str, Decimal | None]], Decimal | None]


CASHFLOW_METRIC_CALCULATORS: dict[str, MetricCalculator] = {
    # =========================================================
    # 1. 经营现金流入结构 operating_cash_inflows
    # =========================================================
    "sales_cash_received": lambda c: c["c_fr_sale_sg"],

    "operating_cash_inflow_total": lambda c: c["c_inf_fr_operate_a"],

    "sales_cash_inflow_share": lambda c: safe_div(
        c["c_fr_sale_sg"],
        c["c_inf_fr_operate_a"],
    ),

    "other_operating_inflow_share": lambda c: safe_div(
        c["c_fr_oth_operate_a"],
        c["c_inf_fr_operate_a"],
    ),

    # =========================================================
    # 2. 经营现金流出结构 operating_cash_outflows
    # =========================================================
    "goods_services_cash_paid": lambda c: c["c_paid_goods_s"],

    "employee_cash_paid": lambda c: c["c_paid_to_for_empl"],

    "taxes_cash_paid": lambda c: c["c_paid_for_taxes"],

    "operating_cash_outflow_total": lambda c: c["st_cash_out_act"],

    "purchase_cash_outflow_share": lambda c: safe_div(
        c["c_paid_goods_s"],
        c["st_cash_out_act"],
    ),

    # =========================================================
    # 3. 经营现金流净额 operating_cash_net
    # =========================================================
    "operating_net_cashflow": lambda c: c["n_cashflow_act"],

    "operating_cashflow_inflow_margin": lambda c: safe_div(
        c["n_cashflow_act"],
        c["c_inf_fr_operate_a"],
    ),

    # =========================================================
    # 4. 投资现金流与资本开支 investing_capex_structure
    # =========================================================
    "investment_cash_inflow_total": lambda c: c["stot_inflows_inv_act"],

    "capex_cash_paid": lambda c: c["c_pay_acq_const_fiolta"],

    "investment_cash_paid": lambda c: c["c_paid_invest"],

    "investment_cash_outflow_total": lambda c: c["stot_out_inv_act"],

    "investing_net_cashflow": lambda c: c["n_cashflow_inv_act"],

    "capex_outflow_share": lambda c: safe_div(
        c["c_pay_acq_const_fiolta"],
        c["stot_out_inv_act"],
    ),

    # =========================================================
    # 5. 筹资现金流结构 financing_cashflow_structure
    # =========================================================
    "equity_financing_cash_received": lambda c: c["c_recp_cap_contrib"],

    "debt_financing_cash_received": lambda c: c["debt_financing_cash_received"],

    "financing_cash_inflow_total": lambda c: c["stot_cash_in_fnc_act"],

    "debt_repayment_cash_paid": lambda c: c["c_prepay_amt_borr"],

    "dividend_interest_cash_paid": lambda c: c["c_pay_dist_dpcp_int_exp"],

    "financing_cash_outflow_total": lambda c: c["stot_cashout_fnc_act"],

    "financing_net_cashflow": lambda c: c["n_cash_flows_fnc_act"],

    # =========================================================
    # 6. 现金及现金等价物变化 cash_balance_change
    # =========================================================
    "beginning_cash_equivalent": lambda c: c["c_cash_equ_beg_period"],

    "ending_cash_equivalent": lambda c: c["c_cash_equ_end_period"],

    "net_cash_equivalent_increase": lambda c: c["n_incr_cash_cash_equ"],

    # =========================================================
    # 7. 经营现金流间接法调节 indirect_operating_reconciliation
    # =========================================================
    "indirect_net_profit_base": lambda c: c["net_profit"],

    "depreciation_amortization_amount": lambda c: c["depreciation_amortization_amount"],

    "inventory_decrease_cash_effect": lambda c: c["decr_inventories"],

    "operating_receivable_decrease_cash_effect": lambda c: c["decr_oper_payable"],

    "operating_payable_increase_cash_effect": lambda c: c["incr_oper_payable"],

    "indirect_operating_cashflow": lambda c: c["im_net_cashflow_oper_act"],
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

    注意：
    - 现金流项目可以为负数，保留负号即可。
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

def build_cashflow_evidence(
    records: list[Any],
    metric_groups: list[str],
) -> dict[str, Any]:
    """
    CashFlow evidence tool 核心函数。

    输入：
    - records: 从 LangGraph state 里取出的 CashFlow ORM 列表
    - metric_groups: ReAct Agent 指定的 group 列表

    输出：
    - 只输出 name、unit、value
    - 不输出 formula、description、depends_on
    - value 使用 [["YYYY-MM-DD", value], ...] 的紧凑结构
    """

    if not records:
        return {"cashflow": []}

    selected_groups = [
        group for group in metric_groups
        if group in CASHFLOW_GROUPS
    ]

    if not selected_groups:
        return {"cashflow": []}

    sorted_records = sorted(
        records,
        key=lambda r: get_period(r),
    )

    contexts = [
        {
            "period": get_period(record),
            "ctx": build_cashflow_context(record),
        }
        for record in sorted_records
    ]

    result = []

    for group_code in selected_groups:
        group_config = CASHFLOW_GROUPS[group_code]
        metric_codes = group_config["metrics"]

        group_metrics = []

        for metric_code in metric_codes:
            registry_item = CASHFLOW_METRIC_REGISTRY.get(metric_code)
            calculator = CASHFLOW_METRIC_CALCULATORS.get(metric_code)

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

    return {"cashflow": result}


# =========================
# 6. ReAct runtime wrapper 可选
# =========================

class CashFlowEvidenceRuntimeTool:
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
        return build_cashflow_evidence(
            records=self.records,
            metric_groups=metric_groups,
        )