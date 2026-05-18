from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Callable

from app.skills.analysis.metric_groups import CROSS_STATEMENT_GROUPS
from app.skills.analysis.metric_registry import CROSS_STATEMENT_METRIC_REGISTRY


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


def pick_first_not_none(*values: Any) -> Decimal | None:
    for value in values:
        decimal_value = to_decimal(value)
        if decimal_value is not None:
            return decimal_value
    return None


def get_field(record: Any | None, field_name: str) -> Decimal | None:
    """
    同时兼容 SQLAlchemy ORM 对象、dict 和 None。
    """
    if record is None:
        return None

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


def build_period_index(records: list[Any]) -> dict[str, Any]:
    """
    按 end_date 建索引。

    如果同一 period 有多条记录，默认保留最后一条。
    正常情况下 Data 阶段应该已经处理过 report_type / update_flag。
    """
    period_index: dict[str, Any] = {}

    for record in records:
        period = get_period(record)
        if not period:
            continue
        period_index[period] = record

    return period_index


# =========================
# 2. BalanceSheet effective 字段
# =========================

def effective_receivables(balance_record: Any | None) -> Decimal | None:
    """
    经营性应收基础口径：

    优先：
    - accounts_receiv_bill

    兜底：
    - notes_receiv + accounts_receiv
    """
    return pick_first_not_none(
        get_field(balance_record, "accounts_receiv_bill"),
        safe_add(
            get_field(balance_record, "notes_receiv"),
            get_field(balance_record, "accounts_receiv"),
        ),
    )


def effective_payables(balance_record: Any | None) -> Decimal | None:
    """
    经营性应付基础口径：

    优先：
    - accounts_pay

    兜底：
    - notes_payable + acct_payable
    """
    return pick_first_not_none(
        get_field(balance_record, "accounts_pay"),
        safe_add(
            get_field(balance_record, "notes_payable"),
            get_field(balance_record, "acct_payable"),
        ),
    )


# =========================
# 3. 单期跨表上下文构造
# =========================

def build_cross_statement_context(
    income_record: Any | None,
    balance_record: Any | None,
    cashflow_record: Any | None,
    fina_indicator_record: Any | None,
) -> dict[str, Decimal | None]:
    """
    构建某一个 report period 的跨表计算上下文。

    注意：
    - ctx 只在 tool 内部使用；
    - 不直接返回给 LLM；
    - 这里聚合 Income / BalanceSheet / CashFlow / FinaIndicator 的必要字段；
    - 缺失字段保持 None，不猜、不补。
    """

    ctx: dict[str, Decimal | None] = {
        # =========================
        # Income
        # =========================
        "income_revenue": get_field(income_record, "revenue"),
        "income_n_income": get_field(income_record, "n_income"),
        "income_n_income_attr_p": get_field(income_record, "n_income_attr_p"),
        "income_operate_profit": get_field(income_record, "operate_profit"),

        "income_assets_impair_loss": get_field(income_record, "assets_impair_loss"),
        "income_credit_impa_loss": get_field(income_record, "credit_impa_loss"),
        "income_oth_impair_loss_assets": get_field(income_record, "oth_impair_loss_assets"),

        # =========================
        # BalanceSheet
        # =========================
        "bs_inventories": get_field(balance_record, "inventories"),
        "bs_contract_assets": get_field(balance_record, "contract_assets"),
        "bs_adv_receipts": get_field(balance_record, "adv_receipts"),
        "bs_contract_liab": get_field(balance_record, "contract_liab"),

        "bs_st_borr": get_field(balance_record, "st_borr"),
        "bs_non_cur_liab_due_1y": get_field(balance_record, "non_cur_liab_due_1y"),
        "bs_st_bonds_payable": get_field(balance_record, "st_bonds_payable"),

        # =========================
        # CashFlow
        # =========================
        "cf_c_fr_sale_sg": get_field(cashflow_record, "c_fr_sale_sg"),
        "cf_n_cashflow_act": get_field(cashflow_record, "n_cashflow_act"),
        "cf_c_pay_acq_const_fiolta": get_field(cashflow_record, "c_pay_acq_const_fiolta"),
        "cf_c_prepay_amt_borr": get_field(cashflow_record, "c_prepay_amt_borr"),
        "cf_c_pay_dist_dpcp_int_exp": get_field(cashflow_record, "c_pay_dist_dpcp_int_exp"),

        "cf_depr_fa_coga_dpba": get_field(cashflow_record, "depr_fa_coga_dpba"),
        "cf_amort_intang_assets": get_field(cashflow_record, "amort_intang_assets"),
        "cf_decr_inventories": get_field(cashflow_record, "decr_inventories"),
        "cf_decr_oper_payable": get_field(cashflow_record, "decr_oper_payable"),
        "cf_incr_oper_payable": get_field(cashflow_record, "incr_oper_payable"),

        # =========================
        # FinaIndicator
        # =========================
        "fi_profit_dedt": get_field(fina_indicator_record, "profit_dedt"),
        "fi_netdebt": get_field(fina_indicator_record, "netdebt"),
    }

    # =========================
    # BalanceSheet derived context
    # =========================

    ctx["bs_effective_receivables"] = effective_receivables(balance_record)

    ctx["bs_operating_receivables"] = safe_add(
        ctx["bs_effective_receivables"],
        ctx["bs_contract_assets"],
    )

    ctx["bs_effective_payables"] = effective_payables(balance_record)

    ctx["bs_operating_payables"] = safe_add(
        ctx["bs_effective_payables"],
        ctx["bs_adv_receipts"],
        ctx["bs_contract_liab"],
    )

    ctx["bs_net_operating_working_capital"] = safe_sub(
        safe_add(
            ctx["bs_operating_receivables"],
            ctx["bs_inventories"],
        ),
        ctx["bs_operating_payables"],
    )

    ctx["bs_short_term_interest_debt"] = safe_add(
        ctx["bs_st_borr"],
        ctx["bs_non_cur_liab_due_1y"],
        ctx["bs_st_bonds_payable"],
    )

    # =========================
    # Income derived context
    # =========================

    ctx["income_total_impairment_loss"] = safe_add(
        ctx["income_assets_impair_loss"],
        ctx["income_credit_impa_loss"],
        ctx["income_oth_impair_loss_assets"],
    )

    # =========================
    # CashFlow derived context
    # =========================

    ctx["cf_simple_free_cashflow"] = safe_sub(
        ctx["cf_n_cashflow_act"],
        ctx["cf_c_pay_acq_const_fiolta"],
    )

    ctx["cf_depreciation_amortization"] = safe_add(
        ctx["cf_depr_fa_coga_dpba"],
        ctx["cf_amort_intang_assets"],
    )

    ctx["cf_working_capital_adjustment"] = safe_add(
        ctx["cf_decr_inventories"],
        ctx["cf_decr_oper_payable"],
        ctx["cf_incr_oper_payable"],
    )

    return ctx


# =========================
# 4. 指标计算函数
# =========================

MetricCalculator = Callable[[dict[str, Decimal | None]], Decimal | None]


CROSS_STATEMENT_METRIC_CALCULATORS: dict[str, MetricCalculator] = {
    # =========================================================
    # 1. 收入质量诊断 revenue_quality
    # =========================================================
    "sales_cash_to_revenue": lambda c: safe_div(
        c["cf_c_fr_sale_sg"],
        c["income_revenue"],
    ),

    "operating_receivables_to_revenue": lambda c: safe_div(
        c["bs_operating_receivables"],
        c["income_revenue"],
    ),

    "receivable_inventory_to_revenue": lambda c: safe_div(
        safe_add(
            c["bs_operating_receivables"],
            c["bs_inventories"],
        ),
        c["income_revenue"],
    ),

    # =========================================================
    # 2. 利润质量诊断 profit_quality
    # =========================================================
    "ocf_to_net_income": lambda c: safe_div(
        c["cf_n_cashflow_act"],
        c["income_n_income"],
    ),

    "profit_cash_gap": lambda c: safe_sub(
        c["cf_n_cashflow_act"],
        c["income_n_income"],
    ),

    "deducted_profit_to_parent_net_income": lambda c: safe_div(
        c["fi_profit_dedt"],
        c["income_n_income_attr_p"],
    ),

    "impairment_to_parent_net_income": lambda c: safe_div(
        c["income_total_impairment_loss"],
        c["income_n_income_attr_p"],
    ),

    # =========================================================
    # 3. 现金转化质量诊断 cash_conversion_quality
    # =========================================================
    "simple_free_cashflow": lambda c: c["cf_simple_free_cashflow"],

    "simple_fcf_to_net_income": lambda c: safe_div(
        c["cf_simple_free_cashflow"],
        c["income_n_income"],
    ),

    "ocf_to_operating_profit": lambda c: safe_div(
        c["cf_n_cashflow_act"],
        c["income_operate_profit"],
    ),

    # =========================================================
    # 4. 偿债压力诊断 debt_service_pressure
    # =========================================================
    "ocf_to_short_interest_debt": lambda c: safe_div(
        c["cf_n_cashflow_act"],
        c["bs_short_term_interest_debt"],
    ),

    "debt_repayment_to_ocf": lambda c: safe_div(
        c["cf_c_prepay_amt_borr"],
        c["cf_n_cashflow_act"],
    ),

    "dividend_interest_to_ocf": lambda c: safe_div(
        c["cf_c_pay_dist_dpcp_int_exp"],
        c["cf_n_cashflow_act"],
    ),

    "netdebt_to_ocf": lambda c: safe_div(
        c["fi_netdebt"],
        c["cf_n_cashflow_act"],
    ),

    # =========================================================
    # 5. 资本开支与扩张压力 capex_expansion_pressure
    # =========================================================
    "capex_to_ocf": lambda c: safe_div(
        c["cf_c_pay_acq_const_fiolta"],
        c["cf_n_cashflow_act"],
    ),

    "capex_to_revenue": lambda c: safe_div(
        c["cf_c_pay_acq_const_fiolta"],
        c["income_revenue"],
    ),

    "capex_to_depreciation_amortization": lambda c: safe_div(
        c["cf_c_pay_acq_const_fiolta"],
        c["cf_depreciation_amortization"],
    ),

    # =========================================================
    # 6. 营运资本占款压力 working_capital_pressure
    # =========================================================
    "net_operating_working_capital_to_revenue": lambda c: safe_div(
        c["bs_net_operating_working_capital"],
        c["income_revenue"],
    ),

    "operating_receivables_to_sales_cash": lambda c: safe_div(
        c["bs_operating_receivables"],
        c["cf_c_fr_sale_sg"],
    ),

    "working_capital_adjustment_to_ocf": lambda c: safe_div(
        c["cf_working_capital_adjustment"],
        c["cf_n_cashflow_act"],
    ),
}


# =========================
# 5. 输出压缩
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
    - cross tool 中有些 amount 和 ratio 可能为负，保留负号即可。
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
# 6. 核心 evidence tool
# =========================

def build_cross_statement_evidence(
    income_records: list[Any],
    balance_sheet_records: list[Any],
    cashflow_records: list[Any],
    fina_indicator_records: list[Any],
    metric_groups: list[str],
) -> dict[str, Any]:
    """
    Cross-statement evidence tool 核心函数。

    输入：
    - income_records: Data 阶段准备好的 Income ORM 列表
    - balance_sheet_records: Data 阶段准备好的 BalanceSheet ORM 列表
    - cashflow_records: Data 阶段准备好的 CashFlow ORM 列表
    - fina_indicator_records: Data 阶段准备好的 FinaIndicator ORM 列表
    - metric_groups: ReAct Agent 指定的 group 列表

    输出：
    - 只输出 name、unit、value
    - 不输出 formula、description、depends_on
    - value 使用 [["YYYY-MM-DD", value], ...] 的紧凑结构

    定位：
    - 不补数据；
    - 不查数据库；
    - 不替代四个单表 tool；
    - 只做跨表诊断 evidence。
    """

    selected_groups = [
        group for group in metric_groups
        if group in CROSS_STATEMENT_GROUPS
    ]

    if not selected_groups:
        return {"cross_statement": []}

    income_by_period = build_period_index(income_records)
    balance_by_period = build_period_index(balance_sheet_records)
    cashflow_by_period = build_period_index(cashflow_records)
    fina_by_period = build_period_index(fina_indicator_records)

    all_periods = sorted(
        set(income_by_period)
        | set(balance_by_period)
        | set(cashflow_by_period)
        | set(fina_by_period)
    )

    if not all_periods:
        return {"cross_statement": []}

    contexts = []

    for period in all_periods:
        income_record = income_by_period.get(period)
        balance_record = balance_by_period.get(period)
        cashflow_record = cashflow_by_period.get(period)
        fina_indicator_record = fina_by_period.get(period)

        contexts.append(
            {
                "period": period,
                "ctx": build_cross_statement_context(
                    income_record=income_record,
                    balance_record=balance_record,
                    cashflow_record=cashflow_record,
                    fina_indicator_record=fina_indicator_record,
                ),
            }
        )

    result = []

    for group_code in selected_groups:
        group_config = CROSS_STATEMENT_GROUPS[group_code]
        metric_codes = group_config["metrics"]

        group_metrics = []

        for metric_code in metric_codes:
            registry_item = CROSS_STATEMENT_METRIC_REGISTRY.get(metric_code)
            calculator = CROSS_STATEMENT_METRIC_CALCULATORS.get(metric_code)

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

    return {"cross_statement": result}


# =========================
# 7. ReAct runtime wrapper 可选
# =========================

class CrossStatementEvidenceRuntimeTool:
    """
    给 ReAct Agent 使用的轻量包装。

    注意：
    - 四类 records 不由 LLM 传入；
    - records 应该来自 LangGraph state；
    - LLM 只需要选择 metric_groups。
    """

    def __init__(
        self,
        income_records: list[Any],
        balance_sheet_records: list[Any],
        cashflow_records: list[Any],
        fina_indicator_records: list[Any],
    ):
        self.income_records = income_records
        self.balance_sheet_records = balance_sheet_records
        self.cashflow_records = cashflow_records
        self.fina_indicator_records = fina_indicator_records

    def run(self, metric_groups: list[str]) -> dict[str, Any]:
        return build_cross_statement_evidence(
            income_records=self.income_records,
            balance_sheet_records=self.balance_sheet_records,
            cashflow_records=self.cashflow_records,
            fina_indicator_records=self.fina_indicator_records,
            metric_groups=metric_groups,
        )