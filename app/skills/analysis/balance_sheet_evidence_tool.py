from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Callable

from app.skills.analysis.metric_groups import BALANCE_SHEET_GROUPS
from app.skills.analysis.metric_registry import BALANCE_SHEET_METRIC_REGISTRY


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


def pick_first_not_none(*values: Any) -> Decimal | None:
    for value in values:
        decimal_value = to_decimal(value)
        if decimal_value is not None:
            return decimal_value
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
    同时兼容 ORM 对象和 dict。
    """
    if isinstance(record, dict):
        return to_decimal(record.get(field_name))

    return to_decimal(getattr(record, field_name, None))


def get_period(record: Any) -> str:
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
# 2. effective 字段口径
# =========================

def effective_receivables(record: Any) -> Decimal | None:
    """
    应收票据及应收账款统一口径。

    优先：
    - accounts_receiv_bill

    兜底：
    - notes_receiv + accounts_receiv
    """
    return pick_first_not_none(
        get_field(record, "accounts_receiv_bill"),
        safe_add(
            get_field(record, "notes_receiv"),
            get_field(record, "accounts_receiv"),
        ),
    )


def effective_payables(record: Any) -> Decimal | None:
    """
    应付票据及应付账款统一口径。

    优先：
    - accounts_pay

    兜底：
    - notes_payable + acct_payable
    """
    return pick_first_not_none(
        get_field(record, "accounts_pay"),
        safe_add(
            get_field(record, "notes_payable"),
            get_field(record, "acct_payable"),
        ),
    )


def effective_fixed_assets(record: Any) -> Decimal | None:
    """
    固定资产统一口径。

    优先：
    - fix_assets_total

    兜底：
    - fix_assets
    """
    return pick_first_not_none(
        get_field(record, "fix_assets_total"),
        get_field(record, "fix_assets"),
    )


def effective_cip(record: Any) -> Decimal | None:
    """
    在建工程统一口径。

    优先：
    - cip_total

    兜底：
    - cip

    如果你的 ORM 暂时没有 cip 字段，也没关系，会自动只用 cip_total。
    """
    return pick_first_not_none(
        get_field(record, "cip_total"),
        get_field(record, "cip"),
    )


# =========================
# 3. 单期上下文构造
# =========================

def build_balance_sheet_context(record: Any) -> dict[str, Decimal | None]:
    """
    把 ORM record 转成计算上下文。

    注意：
    - 这里不会返回给 LLM；
    - 只是 tool 内部计算用。
    """

    ctx: dict[str, Decimal | None] = {
        # 资产端
        "money_cap": get_field(record, "money_cap"),
        "total_cur_assets": get_field(record, "total_cur_assets"),
        "total_nca": get_field(record, "total_nca"),
        "total_assets": get_field(record, "total_assets"),
        "inventories": get_field(record, "inventories"),
        "contract_assets": get_field(record, "contract_assets"),
        "goodwill": get_field(record, "goodwill"),
        "intan_assets": get_field(record, "intan_assets"),

        # 负债端
        "st_borr": get_field(record, "st_borr"),
        "non_cur_liab_due_1y": get_field(record, "non_cur_liab_due_1y"),
        "st_bonds_payable": get_field(record, "st_bonds_payable"),
        "lt_borr": get_field(record, "lt_borr"),
        "bond_payable": get_field(record, "bond_payable"),
        "lease_liab": get_field(record, "lease_liab"),
        "adv_receipts": get_field(record, "adv_receipts"),
        "contract_liab": get_field(record, "contract_liab"),
        "total_cur_liab": get_field(record, "total_cur_liab"),
        "total_liab": get_field(record, "total_liab"),

        # 权益端
        "total_hldr_eqy_inc_min_int": get_field(record, "total_hldr_eqy_inc_min_int"),

        # 统一口径字段
        "effective_receivables": effective_receivables(record),
        "effective_payables": effective_payables(record),
        "effective_fixed_assets": effective_fixed_assets(record),
        "effective_cip": effective_cip(record),
    }

    # 派生中间变量
    ctx["interest_bearing_debt"] = safe_add(
        ctx["st_borr"],
        ctx["non_cur_liab_due_1y"],
        ctx["st_bonds_payable"],
        ctx["lt_borr"],
        ctx["bond_payable"],
        ctx["lease_liab"],
    )

    ctx["short_term_interest_debt"] = safe_add(
        ctx["st_borr"],
        ctx["non_cur_liab_due_1y"],
        ctx["st_bonds_payable"],
    )

    ctx["long_term_interest_debt"] = safe_add(
        ctx["lt_borr"],
        ctx["bond_payable"],
        ctx["lease_liab"],
    )

    ctx["operating_receivables"] = safe_add(
        ctx["effective_receivables"],
        ctx["contract_assets"],
    )

    ctx["operating_payables"] = safe_add(
        ctx["effective_payables"],
        ctx["adv_receipts"],
        ctx["contract_liab"],
    )

    ctx["net_operating_working_capital"] = safe_sub(
        safe_add(ctx["operating_receivables"], ctx["inventories"]),
        ctx["operating_payables"],
    )

    return ctx


# =========================
# 4. 指标计算函数
# =========================

MetricCalculator = Callable[[dict[str, Decimal | None]], Decimal | None]


BALANCE_SHEET_METRIC_CALCULATORS: dict[str, MetricCalculator] = {
    # asset_scale_structure
    "current_asset_ratio": lambda c: safe_div(c["total_cur_assets"], c["total_assets"]),
    "noncurrent_asset_ratio": lambda c: safe_div(c["total_nca"], c["total_assets"]),
    "fixed_asset_ratio": lambda c: safe_div(c["effective_fixed_assets"], c["total_assets"]),
    "cash_asset_ratio": lambda c: safe_div(c["money_cap"], c["total_assets"]),

    # debt_structure
    "short_term_interest_debt": lambda c: c["short_term_interest_debt"],
    "long_term_interest_debt": lambda c: c["long_term_interest_debt"],
    "debt_maturity_pressure": lambda c: safe_div(
        c["short_term_interest_debt"],
        c["interest_bearing_debt"],
    ),

    # solvency_leverage
    "cash_to_short_debt": lambda c: safe_div(
        c["money_cap"],
        c["short_term_interest_debt"],
    ),

    # receivables_inventory
    "operating_receivables": lambda c: c["operating_receivables"],
    "receivable_asset_ratio": lambda c: safe_div(
        c["operating_receivables"],
        c["total_assets"],
    ),
    "inventory_asset_ratio": lambda c: safe_div(c["inventories"], c["total_assets"]),
    "receivable_inventory_ratio": lambda c: safe_div(
        safe_add(c["operating_receivables"], c["inventories"]),
        c["total_assets"],
    ),
    "contract_asset_ratio": lambda c: safe_div(c["contract_assets"], c["total_assets"]),

    # payables_contract_liability
    "operating_payables": lambda c: c["operating_payables"],
    "payable_liability_ratio": lambda c: safe_div(
        c["operating_payables"],
        c["total_liab"],
    ),
    "advance_contract_liab_ratio": lambda c: safe_div(
        safe_add(c["adv_receipts"], c["contract_liab"]),
        c["total_assets"],
    ),
    "net_operating_working_capital": lambda c: c["net_operating_working_capital"],

    # asset_quality_risk
    "goodwill_asset_ratio": lambda c: safe_div(c["goodwill"], c["total_assets"]),
    "intangible_asset_ratio": lambda c: safe_div(c["intan_assets"], c["total_assets"]),
    "goodwill_intangible_ratio": lambda c: safe_div(
        safe_add(c["goodwill"], c["intan_assets"]),
        c["total_assets"],
    ),
    "cip_asset_ratio": lambda c: safe_div(c["effective_cip"], c["total_assets"]),
    "cip_fixed_asset_ratio": lambda c: safe_div(
        c["effective_cip"],
        c["effective_fixed_assets"],
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
    - ratio 保留 4 位小数；
    - amount 默认转为亿元，保留 2 位小数；
    - None 直接返回 None。
    """
    if value is None:
        return None

    if unit == "amount":
        return float(round(value / AMOUNT_SCALE, 2))

    return float(round(value, 4))


def output_unit(unit: str) -> str:
    if unit == "amount":
        return AMOUNT_UNIT
    return unit


# =========================
# 6. 核心 evidence tool
# =========================

def build_balance_sheet_evidence(
    records: list[Any],
    metric_groups: list[str],
) -> dict[str, Any]:
    """
    BalanceSheet evidence tool 核心函数。

    输入：
    - records: 从 LangGraph state 里取出的 BalanceSheet ORM 列表
    - metric_groups: ReAct Agent 指定的 group 列表

    输出：
    - 只输出 name、unit、value
    - value 使用 [["YYYY-MM-DD", value], ...] 的紧凑结构
    """

    if not records:
        return {"balance_sheet": []}

    selected_groups = [
        group for group in metric_groups
        if group in BALANCE_SHEET_GROUPS
    ]

    if not selected_groups:
        return {"balance_sheet": []}

    sorted_records = sorted(
        records,
        key=lambda r: get_period(r),
    )

    contexts = [
        {
            "period": get_period(record),
            "ctx": build_balance_sheet_context(record),
        }
        for record in sorted_records
    ]

    result = []

    for group_code in selected_groups:
        group_config = BALANCE_SHEET_GROUPS[group_code]
        metric_codes = group_config["metrics"]

        group_metrics = []

        for metric_code in metric_codes:
            registry_item = BALANCE_SHEET_METRIC_REGISTRY.get(metric_code)
            calculator = BALANCE_SHEET_METRIC_CALCULATORS.get(metric_code)

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

    return {"balance_sheet": result}


class BalanceSheetEvidenceRuntimeTool:
    def __init__(self, records: list[Any]):
        self.records = records

    def run(self, metric_groups: list[str]) -> dict[str, Any]:
        return build_balance_sheet_evidence(
            records=self.records,
            metric_groups=metric_groups,
        )