# ============================================================
# 2. tool 内部使用的 metric registry
#    大模型不需要知道这些 metric_code
# ============================================================
from typing import Any


# ---------------- INCOME METRICS --------------------
INCOME_METRIC_REGISTRY: dict[str, dict[str, Any]] = {
    # --------------------
    # single_period：单期差值类
    # --------------------
    "gross_profit": {
        "metric_type": "single_period",
        "unit": "CNY",
        "formula": "revenue - oper_cost",
        "operation": "subtract",
        "left": "revenue",
        "right": "oper_cost",
        "source_fields": ["revenue", "oper_cost"],
    },
    "period_expense": {
        "metric_type": "single_period",
        "unit": "CNY",
        "formula": "sell_exp + admin_exp + fin_exp",
        "operation": "sum",
        "fields": ["sell_exp", "admin_exp", "fin_exp"],
        "source_fields": ["sell_exp", "admin_exp", "fin_exp"],
    },
    "total_profit_minus_operating_profit": {
        "metric_type": "single_period",
        "unit": "CNY",
        "formula": "total_profit - operate_profit",
        "operation": "subtract",
        "left": "total_profit",
        "right": "operate_profit",
        "source_fields": ["total_profit", "operate_profit"],
    },
    "total_profit_minus_net_profit": {
        "metric_type": "single_period",
        "unit": "CNY",
        "formula": "total_profit - net_profit",
        "operation": "subtract",
        "left": "total_profit",
        "right": "net_profit",
        "source_fields": ["total_profit", "net_profit"],
    },
    "net_profit_minus_parent_net_profit": {
        "metric_type": "single_period",
        "unit": "CNY",
        "formula": "net_profit - n_income_attr_p",
        "operation": "subtract",
        "left": "net_profit",
        "right": "n_income_attr_p",
        "source_fields": ["net_profit", "n_income_attr_p"],
    },
    "comprehensive_income_minus_parent_net_profit": {
        "metric_type": "single_period",
        "unit": "CNY",
        "formula": "compr_inc_attr_p - n_income_attr_p",
        "operation": "subtract",
        "left": "compr_inc_attr_p",
        "right": "n_income_attr_p",
        "source_fields": ["compr_inc_attr_p", "n_income_attr_p"],
    },
    "basic_eps_minus_diluted_eps": {
        "metric_type": "single_period",
        "unit": "ratio",
        "formula": "basic_eps - diluted_eps",
        "operation": "subtract",
        "left": "basic_eps",
        "right": "diluted_eps",
        "source_fields": ["basic_eps", "diluted_eps"],
    },

    # --------------------
    # composition_ratio：结构比例类
    # --------------------
    "invest_income_to_total_profit": {
        "metric_type": "composition_ratio",
        "unit": "ratio",
        "formula": "invest_income / total_profit",
        "operation": "divide",
        "numerator": "invest_income",
        "denominator": "total_profit",
        "source_fields": ["invest_income", "total_profit"],
    },
    "invest_income_to_net_profit": {
        "metric_type": "composition_ratio",
        "unit": "ratio",
        "formula": "invest_income / net_profit",
        "operation": "divide",
        "numerator": "invest_income",
        "denominator": "net_profit",
        "source_fields": ["invest_income", "net_profit"],
    },
    "assets_impair_loss_to_total_profit": {
        "metric_type": "composition_ratio",
        "unit": "ratio",
        "formula": "assets_impair_loss / total_profit",
        "operation": "divide",
        "numerator": "assets_impair_loss",
        "denominator": "total_profit",
        "source_fields": ["assets_impair_loss", "total_profit"],
    },
    "assets_impair_loss_to_net_profit": {
        "metric_type": "composition_ratio",
        "unit": "ratio",
        "formula": "assets_impair_loss / net_profit",
        "operation": "divide",
        "numerator": "assets_impair_loss",
        "denominator": "net_profit",
        "source_fields": ["assets_impair_loss", "net_profit"],
    },
    "income_tax_to_total_profit": {
        "metric_type": "composition_ratio",
        "unit": "ratio",
        "formula": "income_tax / total_profit",
        "operation": "divide",
        "numerator": "income_tax",
        "denominator": "total_profit",
        "source_fields": ["income_tax", "total_profit"],
    },
    "minority_gain_to_net_profit": {
        "metric_type": "composition_ratio",
        "unit": "ratio",
        "formula": "minority_gain / net_profit",
        "operation": "divide",
        "numerator": "minority_gain",
        "denominator": "net_profit",
        "source_fields": ["minority_gain", "net_profit"],
    },
    "parent_net_profit_to_net_profit": {
        "metric_type": "composition_ratio",
        "unit": "ratio",
        "formula": "n_income_attr_p / net_profit",
        "operation": "divide",
        "numerator": "n_income_attr_p",
        "denominator": "net_profit",
        "source_fields": ["n_income_attr_p", "net_profit"],
    },
    "operating_profit_to_total_profit": {
        "metric_type": "composition_ratio",
        "unit": "ratio",
        "formula": "operate_profit / total_profit",
        "operation": "divide",
        "numerator": "operate_profit",
        "denominator": "total_profit",
        "source_fields": ["operate_profit", "total_profit"],
    },
    "net_profit_to_total_profit": {
        "metric_type": "composition_ratio",
        "unit": "ratio",
        "formula": "net_profit / total_profit",
        "operation": "divide",
        "numerator": "net_profit",
        "denominator": "total_profit",
        "source_fields": ["net_profit", "total_profit"],
    },
    "period_expense_to_gross_profit": {
        "metric_type": "composition_ratio",
        "unit": "ratio",
        "formula": "period_expense / gross_profit",
        "operation": "divide_derived",
        "numerator_derived": "period_expense",
        "denominator_derived": "gross_profit",
        "source_fields": ["sell_exp", "admin_exp", "fin_exp", "revenue", "oper_cost"],
    },

    # --------------------
    # yoy：同比增长率
    # --------------------
    "total_revenue_yoy": {
        "metric_type": "yoy",
        "unit": "ratio",
        "formula": "(cur.total_revenue - base.total_revenue) / base.total_revenue",
        "field": "total_revenue",
        "source_fields": ["total_revenue"],
    },
    "revenue_yoy": {
        "metric_type": "yoy",
        "unit": "ratio",
        "formula": "(cur.revenue - base.revenue) / base.revenue",
        "field": "revenue",
        "source_fields": ["revenue"],
    },
    "total_cogs_yoy": {
        "metric_type": "yoy",
        "unit": "ratio",
        "formula": "(cur.total_cogs - base.total_cogs) / base.total_cogs",
        "field": "total_cogs",
        "source_fields": ["total_cogs"],
    },
    "oper_cost_yoy": {
        "metric_type": "yoy",
        "unit": "ratio",
        "formula": "(cur.oper_cost - base.oper_cost) / base.oper_cost",
        "field": "oper_cost",
        "source_fields": ["oper_cost"],
    },
    "sell_exp_yoy": {
        "metric_type": "yoy",
        "unit": "ratio",
        "formula": "(cur.sell_exp - base.sell_exp) / base.sell_exp",
        "field": "sell_exp",
        "source_fields": ["sell_exp"],
    },
    "admin_exp_yoy": {
        "metric_type": "yoy",
        "unit": "ratio",
        "formula": "(cur.admin_exp - base.admin_exp) / base.admin_exp",
        "field": "admin_exp",
        "source_fields": ["admin_exp"],
    },
    "fin_exp_yoy": {
        "metric_type": "yoy",
        "unit": "ratio",
        "formula": "(cur.fin_exp - base.fin_exp) / base.fin_exp",
        "field": "fin_exp",
        "source_fields": ["fin_exp"],
    },
    "period_expense_yoy": {
        "metric_type": "yoy",
        "unit": "ratio",
        "formula": "(cur.period_expense - base.period_expense) / base.period_expense",
        "derived_field": "period_expense",
        "source_fields": ["sell_exp", "admin_exp", "fin_exp"],
    },
    "operate_profit_yoy": {
        "metric_type": "yoy",
        "unit": "ratio",
        "formula": "(cur.operate_profit - base.operate_profit) / base.operate_profit",
        "field": "operate_profit",
        "source_fields": ["operate_profit"],
    },
    "total_profit_yoy": {
        "metric_type": "yoy",
        "unit": "ratio",
        "formula": "(cur.total_profit - base.total_profit) / base.total_profit",
        "field": "total_profit",
        "source_fields": ["total_profit"],
    },
    "net_profit_yoy": {
        "metric_type": "yoy",
        "unit": "ratio",
        "formula": "(cur.net_profit - base.net_profit) / base.net_profit",
        "field": "net_profit",
        "source_fields": ["net_profit"],
    },
    "parent_net_profit_yoy": {
        "metric_type": "yoy",
        "unit": "ratio",
        "formula": "(cur.n_income_attr_p - base.n_income_attr_p) / base.n_income_attr_p",
        "field": "n_income_attr_p",
        "source_fields": ["n_income_attr_p"],
    },
    "basic_eps_yoy": {
        "metric_type": "yoy",
        "unit": "ratio",
        "formula": "(cur.basic_eps - base.basic_eps) / base.basic_eps",
        "field": "basic_eps",
        "source_fields": ["basic_eps"],
    },
    "diluted_eps_yoy": {
        "metric_type": "yoy",
        "unit": "ratio",
        "formula": "(cur.diluted_eps - base.diluted_eps) / base.diluted_eps",
        "field": "diluted_eps",
        "source_fields": ["diluted_eps"],
    },

    # --------------------
    # yoy_change：同比变化额
    # --------------------
    "total_revenue_yoy_change": {
        "metric_type": "yoy_change",
        "unit": "CNY",
        "formula": "cur.total_revenue - base.total_revenue",
        "field": "total_revenue",
        "source_fields": ["total_revenue"],
    },
    "revenue_yoy_change": {
        "metric_type": "yoy_change",
        "unit": "CNY",
        "formula": "cur.revenue - base.revenue",
        "field": "revenue",
        "source_fields": ["revenue"],
    },
    "oper_cost_yoy_change": {
        "metric_type": "yoy_change",
        "unit": "CNY",
        "formula": "cur.oper_cost - base.oper_cost",
        "field": "oper_cost",
        "source_fields": ["oper_cost"],
    },
    "sell_exp_yoy_change": {
        "metric_type": "yoy_change",
        "unit": "CNY",
        "formula": "cur.sell_exp - base.sell_exp",
        "field": "sell_exp",
        "source_fields": ["sell_exp"],
    },
    "admin_exp_yoy_change": {
        "metric_type": "yoy_change",
        "unit": "CNY",
        "formula": "cur.admin_exp - base.admin_exp",
        "field": "admin_exp",
        "source_fields": ["admin_exp"],
    },
    "fin_exp_yoy_change": {
        "metric_type": "yoy_change",
        "unit": "CNY",
        "formula": "cur.fin_exp - base.fin_exp",
        "field": "fin_exp",
        "source_fields": ["fin_exp"],
    },
    "period_expense_yoy_change": {
        "metric_type": "yoy_change",
        "unit": "CNY",
        "formula": "cur.period_expense - base.period_expense",
        "derived_field": "period_expense",
        "source_fields": ["sell_exp", "admin_exp", "fin_exp"],
    },
    "operate_profit_yoy_change": {
        "metric_type": "yoy_change",
        "unit": "CNY",
        "formula": "cur.operate_profit - base.operate_profit",
        "field": "operate_profit",
        "source_fields": ["operate_profit"],
    },
    "total_profit_yoy_change": {
        "metric_type": "yoy_change",
        "unit": "CNY",
        "formula": "cur.total_profit - base.total_profit",
        "field": "total_profit",
        "source_fields": ["total_profit"],
    },
    "net_profit_yoy_change": {
        "metric_type": "yoy_change",
        "unit": "CNY",
        "formula": "cur.net_profit - base.net_profit",
        "field": "net_profit",
        "source_fields": ["net_profit"],
    },
    "parent_net_profit_yoy_change": {
        "metric_type": "yoy_change",
        "unit": "CNY",
        "formula": "cur.n_income_attr_p - base.n_income_attr_p",
        "field": "n_income_attr_p",
        "source_fields": ["n_income_attr_p"],
    },
    "basic_eps_yoy_change": {
        "metric_type": "yoy_change",
        "unit": "ratio",
        "formula": "cur.basic_eps - base.basic_eps",
        "field": "basic_eps",
        "source_fields": ["basic_eps"],
    },
    "diluted_eps_yoy_change": {
        "metric_type": "yoy_change",
        "unit": "ratio",
        "formula": "cur.diluted_eps - base.diluted_eps",
        "field": "diluted_eps",
        "source_fields": ["diluted_eps"],
    },

    # --------------------
    # growth_spread：增长率差值
    # --------------------
    "net_profit_yoy_minus_revenue_yoy": {
        "metric_type": "growth_spread",
        "unit": "ratio",
        "formula": "net_profit_yoy - revenue_yoy",
        "depends_on": ["net_profit_yoy", "revenue_yoy"],
        "source_fields": ["net_profit", "revenue"],
    },
    "parent_net_profit_yoy_minus_revenue_yoy": {
        "metric_type": "growth_spread",
        "unit": "ratio",
        "formula": "parent_net_profit_yoy - revenue_yoy",
        "depends_on": ["parent_net_profit_yoy", "revenue_yoy"],
        "source_fields": ["n_income_attr_p", "revenue"],
    },
    "operate_profit_yoy_minus_revenue_yoy": {
        "metric_type": "growth_spread",
        "unit": "ratio",
        "formula": "operate_profit_yoy - revenue_yoy",
        "depends_on": ["operate_profit_yoy", "revenue_yoy"],
        "source_fields": ["operate_profit", "revenue"],
    },
    "oper_cost_yoy_minus_revenue_yoy": {
        "metric_type": "growth_spread",
        "unit": "ratio",
        "formula": "oper_cost_yoy - revenue_yoy",
        "depends_on": ["oper_cost_yoy", "revenue_yoy"],
        "source_fields": ["oper_cost", "revenue"],
    },
    "period_expense_yoy_minus_revenue_yoy": {
        "metric_type": "growth_spread",
        "unit": "ratio",
        "formula": "period_expense_yoy - revenue_yoy",
        "depends_on": ["period_expense_yoy", "revenue_yoy"],
        "source_fields": ["sell_exp", "admin_exp", "fin_exp", "revenue"],
    },

    # --------------------
    # cagr：区间复合增长率
    # --------------------
    "total_revenue_cagr": {
        "metric_type": "cagr",
        "unit": "ratio",
        "formula": "(end.total_revenue / start.total_revenue) ** (1 / years) - 1",
        "field": "total_revenue",
        "source_fields": ["total_revenue"],
    },
    "revenue_cagr": {
        "metric_type": "cagr",
        "unit": "ratio",
        "formula": "(end.revenue / start.revenue) ** (1 / years) - 1",
        "field": "revenue",
        "source_fields": ["revenue"],
    },
    "net_profit_cagr": {
        "metric_type": "cagr",
        "unit": "ratio",
        "formula": "(end.net_profit / start.net_profit) ** (1 / years) - 1",
        "field": "net_profit",
        "source_fields": ["net_profit"],
    },
    "parent_net_profit_cagr": {
        "metric_type": "cagr",
        "unit": "ratio",
        "formula": "(end.n_income_attr_p / start.n_income_attr_p) ** (1 / years) - 1",
        "field": "n_income_attr_p",
        "source_fields": ["n_income_attr_p"],
    },
    "basic_eps_cagr": {
        "metric_type": "cagr",
        "unit": "ratio",
        "formula": "(end.basic_eps / start.basic_eps) ** (1 / years) - 1",
        "field": "basic_eps",
        "source_fields": ["basic_eps"],
    },
}
# ============================================================
# 指标中文名称映射
# 给 LLM 返回 compact metrics 时使用
# ============================================================

INCOME_METRIC_NAME_MAP: dict[str, str] = {
    # --------------------
    # single_period：单期差值类
    # --------------------
    "gross_profit": "毛利额",
    "period_expense": "三费合计",
    "total_profit_minus_operating_profit": "利润总额与营业利润差额",
    "total_profit_minus_net_profit": "利润总额与净利润差额",
    "net_profit_minus_parent_net_profit": "净利润与归母净利润差额",
    "comprehensive_income_minus_parent_net_profit": "归母综合收益与归母净利润差额",
    "basic_eps_minus_diluted_eps": "基本每股收益与稀释每股收益差额",

    # --------------------
    # composition_ratio：结构比例类
    # --------------------
    "invest_income_to_total_profit": "投资收益占利润总额比例",
    "invest_income_to_net_profit": "投资收益占净利润比例",
    "assets_impair_loss_to_total_profit": "资产减值损失占利润总额比例",
    "assets_impair_loss_to_net_profit": "资产减值损失占净利润比例",
    "income_tax_to_total_profit": "所得税费用占利润总额比例",
    "minority_gain_to_net_profit": "少数股东损益占净利润比例",
    "parent_net_profit_to_net_profit": "归母净利润占净利润比例",
    "operating_profit_to_total_profit": "营业利润占利润总额比例",
    "net_profit_to_total_profit": "净利润占利润总额比例",
    "period_expense_to_gross_profit": "三费合计占毛利额比例",

    # --------------------
    # yoy：同比增长率
    # --------------------
    "total_revenue_yoy": "营业总收入同比增长率",
    "revenue_yoy": "营业收入同比增长率",
    "total_cogs_yoy": "营业总成本同比增长率",
    "oper_cost_yoy": "营业成本同比增长率",
    "sell_exp_yoy": "销售费用同比增长率",
    "admin_exp_yoy": "管理费用同比增长率",
    "fin_exp_yoy": "财务费用同比增长率",
    "period_expense_yoy": "三费合计同比增长率",
    "operate_profit_yoy": "营业利润同比增长率",
    "total_profit_yoy": "利润总额同比增长率",
    "net_profit_yoy": "净利润同比增长率",
    "parent_net_profit_yoy": "归母净利润同比增长率",
    "basic_eps_yoy": "基本每股收益同比增长率",
    "diluted_eps_yoy": "稀释每股收益同比增长率",

    # --------------------
    # yoy_change：同比变化额
    # --------------------
    "total_revenue_yoy_change": "营业总收入同比变化额",
    "revenue_yoy_change": "营业收入同比变化额",
    "oper_cost_yoy_change": "营业成本同比变化额",
    "sell_exp_yoy_change": "销售费用同比变化额",
    "admin_exp_yoy_change": "管理费用同比变化额",
    "fin_exp_yoy_change": "财务费用同比变化额",
    "period_expense_yoy_change": "三费合计同比变化额",
    "operate_profit_yoy_change": "营业利润同比变化额",
    "total_profit_yoy_change": "利润总额同比变化额",
    "net_profit_yoy_change": "净利润同比变化额",
    "parent_net_profit_yoy_change": "归母净利润同比变化额",
    "basic_eps_yoy_change": "基本每股收益同比变化额",
    "diluted_eps_yoy_change": "稀释每股收益同比变化额",

    # --------------------
    # growth_spread：增长率差值
    # --------------------
    "net_profit_yoy_minus_revenue_yoy": "净利润同比增速减营业收入同比增速",
    "parent_net_profit_yoy_minus_revenue_yoy": "归母净利润同比增速减营业收入同比增速",
    "operate_profit_yoy_minus_revenue_yoy": "营业利润同比增速减营业收入同比增速",
    "oper_cost_yoy_minus_revenue_yoy": "营业成本同比增速减营业收入同比增速",
    "period_expense_yoy_minus_revenue_yoy": "三费合计同比增速减营业收入同比增速",

    # --------------------
    # cagr：区间复合增长率
    # --------------------
    "total_revenue_cagr": "营业总收入复合年增长率",
    "revenue_cagr": "营业收入复合年增长率",
    "net_profit_cagr": "净利润复合年增长率",
    "parent_net_profit_cagr": "归母净利润复合年增长率",
    "basic_eps_cagr": "基本每股收益复合年增长率",
}


def attach_income_metric_names() -> None:
    """
    给 INCOME_METRIC_REGISTRY 中的每个 metric_code 注入中文 name。
    如果有指标漏配 name，会直接抛错，避免后续 LLM 看不懂指标。
    """
    missing_names = []

    for metric_code, metric_def in INCOME_METRIC_REGISTRY.items():
        name = INCOME_METRIC_NAME_MAP.get(metric_code)

        if not name:
            missing_names.append(metric_code)
            continue

        metric_def["name"] = name

    if missing_names:
        raise ValueError(
            "Missing income metric names: "
            + ", ".join(missing_names)
        )

# 在模块加载时执行一次
attach_income_metric_names()

# ---------------- BALANCE METRICS ------------------
BALANCE_SHEET_METRIC_REGISTRY: dict[str, dict[str, Any]] = {
    # ========================================================
    # single_period：单期组合项 / 差值类
    # ========================================================
    "cash_and_trading_assets": {
        "name": "货币资金与交易性金融资产合计",
        "metric_type": "single_period",
        "unit": "CNY",
        "formula": "money_cap + trad_asset",
        "operation": "sum",
        "fields": ["money_cap", "trad_asset"],
        "source_fields": ["money_cap", "trad_asset"],
    },
    "receivables_total": {
        "name": "应收票据与应收账款合计",
        "metric_type": "single_period",
        "unit": "CNY",
        "formula": "notes_receiv + accounts_receiv",
        "operation": "sum",
        "fields": ["notes_receiv", "accounts_receiv"],
        "source_fields": ["notes_receiv", "accounts_receiv"],
    },
    "payables_total": {
        "name": "应付票据与应付账款合计",
        "metric_type": "single_period",
        "unit": "CNY",
        "formula": "notes_payable + acct_payable",
        "operation": "sum",
        "fields": ["notes_payable", "acct_payable"],
        "source_fields": ["notes_payable", "acct_payable"],
    },
    "minority_equity": {
        "name": "少数股东权益",
        "metric_type": "single_period",
        "unit": "CNY",
        "formula": "total_hldr_eqy_inc_min_int - total_hldr_eqy_exc_min_int",
        "operation": "subtract",
        "left": "total_hldr_eqy_inc_min_int",
        "right": "total_hldr_eqy_exc_min_int",
        "source_fields": [
            "total_hldr_eqy_inc_min_int",
            "total_hldr_eqy_exc_min_int",
        ],
    },

    # ========================================================
    # structure_ratio：资产结构比例
    # ========================================================
    "money_cap_to_total_assets": {
        "name": "货币资金占总资产比例",
        "metric_type": "structure_ratio",
        "unit": "ratio",
        "formula": "money_cap / total_assets",
        "operation": "divide",
        "numerator": "money_cap",
        "denominator": "total_assets",
        "source_fields": ["money_cap", "total_assets"],
    },
    "cash_and_trading_assets_to_total_assets": {
        "name": "货币资金与交易性金融资产合计占总资产比例",
        "metric_type": "structure_ratio",
        "unit": "ratio",
        "formula": "cash_and_trading_assets / total_assets",
        "operation": "divide_derived",
        "numerator_derived": "cash_and_trading_assets",
        "denominator": "total_assets",
        "source_fields": ["money_cap", "trad_asset", "total_assets"],
    },
    "current_assets_to_total_assets": {
        "name": "流动资产占总资产比例",
        "metric_type": "structure_ratio",
        "unit": "ratio",
        "formula": "total_cur_assets / total_assets",
        "operation": "divide",
        "numerator": "total_cur_assets",
        "denominator": "total_assets",
        "source_fields": ["total_cur_assets", "total_assets"],
    },
    "noncurrent_assets_to_total_assets": {
        "name": "非流动资产占总资产比例",
        "metric_type": "structure_ratio",
        "unit": "ratio",
        "formula": "total_nca / total_assets",
        "operation": "divide",
        "numerator": "total_nca",
        "denominator": "total_assets",
        "source_fields": ["total_nca", "total_assets"],
    },
    "fixed_assets_to_total_assets": {
        "name": "固定资产占总资产比例",
        "metric_type": "structure_ratio",
        "unit": "ratio",
        "formula": "fix_assets / total_assets",
        "operation": "divide",
        "numerator": "fix_assets",
        "denominator": "total_assets",
        "source_fields": ["fix_assets", "total_assets"],
    },

    # ========================================================
    # current_asset_ratio：流动资产内部结构比例
    # ========================================================
    "receivables_total_to_current_assets": {
        "name": "应收票据与应收账款合计占流动资产比例",
        "metric_type": "structure_ratio",
        "unit": "ratio",
        "formula": "receivables_total / total_cur_assets",
        "operation": "divide_derived",
        "numerator_derived": "receivables_total",
        "denominator": "total_cur_assets",
        "source_fields": ["notes_receiv", "accounts_receiv", "total_cur_assets"],
    },
    "accounts_receiv_to_current_assets": {
        "name": "应收账款占流动资产比例",
        "metric_type": "structure_ratio",
        "unit": "ratio",
        "formula": "accounts_receiv / total_cur_assets",
        "operation": "divide",
        "numerator": "accounts_receiv",
        "denominator": "total_cur_assets",
        "source_fields": ["accounts_receiv", "total_cur_assets"],
    },
    "inventory_to_current_assets": {
        "name": "存货占流动资产比例",
        "metric_type": "structure_ratio",
        "unit": "ratio",
        "formula": "inventories / total_cur_assets",
        "operation": "divide",
        "numerator": "inventories",
        "denominator": "total_cur_assets",
        "source_fields": ["inventories", "total_cur_assets"],
    },
    "prepayment_to_current_assets": {
        "name": "预付款项占流动资产比例",
        "metric_type": "structure_ratio",
        "unit": "ratio",
        "formula": "prepayment / total_cur_assets",
        "operation": "divide",
        "numerator": "prepayment",
        "denominator": "total_cur_assets",
        "source_fields": ["prepayment", "total_cur_assets"],
    },
    "money_cap_to_current_assets": {
        "name": "货币资金占流动资产比例",
        "metric_type": "structure_ratio",
        "unit": "ratio",
        "formula": "money_cap / total_cur_assets",
        "operation": "divide",
        "numerator": "money_cap",
        "denominator": "total_cur_assets",
        "source_fields": ["money_cap", "total_cur_assets"],
    },

    # ========================================================
    # liability_structure：负债结构比例
    # ========================================================
    "current_liab_to_total_liab": {
        "name": "流动负债占总负债比例",
        "metric_type": "structure_ratio",
        "unit": "ratio",
        "formula": "total_cur_liab / total_liab",
        "operation": "divide",
        "numerator": "total_cur_liab",
        "denominator": "total_liab",
        "source_fields": ["total_cur_liab", "total_liab"],
    },
    "noncurrent_liab_to_total_liab": {
        "name": "非流动负债占总负债比例",
        "metric_type": "structure_ratio",
        "unit": "ratio",
        "formula": "total_ncl / total_liab",
        "operation": "divide",
        "numerator": "total_ncl",
        "denominator": "total_liab",
        "source_fields": ["total_ncl", "total_liab"],
    },
    "short_term_borr_to_total_liab": {
        "name": "短期借款占总负债比例",
        "metric_type": "structure_ratio",
        "unit": "ratio",
        "formula": "short_term_borr / total_liab",
        "operation": "divide",
        "numerator": "short_term_borr",
        "denominator": "total_liab",
        "source_fields": ["short_term_borr", "total_liab"],
    },
    "bond_payable_to_total_liab": {
        "name": "应付债券占总负债比例",
        "metric_type": "structure_ratio",
        "unit": "ratio",
        "formula": "bond_payable / total_liab",
        "operation": "divide",
        "numerator": "bond_payable",
        "denominator": "total_liab",
        "source_fields": ["bond_payable", "total_liab"],
    },
    "payables_total_to_total_liab": {
        "name": "应付票据与应付账款合计占总负债比例",
        "metric_type": "structure_ratio",
        "unit": "ratio",
        "formula": "payables_total / total_liab",
        "operation": "divide_derived",
        "numerator_derived": "payables_total",
        "denominator": "total_liab",
        "source_fields": ["notes_payable", "acct_payable", "total_liab"],
    },

    # ========================================================
    # equity_structure：权益结构比例
    # ========================================================
    "parent_equity_to_total_equity": {
        "name": "归母权益占股东权益比例",
        "metric_type": "structure_ratio",
        "unit": "ratio",
        "formula": "total_hldr_eqy_exc_min_int / total_hldr_eqy_inc_min_int",
        "operation": "divide",
        "numerator": "total_hldr_eqy_exc_min_int",
        "denominator": "total_hldr_eqy_inc_min_int",
        "source_fields": [
            "total_hldr_eqy_exc_min_int",
            "total_hldr_eqy_inc_min_int",
        ],
    },
    "minority_equity_to_total_equity": {
        "name": "少数股东权益占股东权益比例",
        "metric_type": "structure_ratio",
        "unit": "ratio",
        "formula": "minority_equity / total_hldr_eqy_inc_min_int",
        "operation": "divide_derived",
        "numerator_derived": "minority_equity",
        "denominator": "total_hldr_eqy_inc_min_int",
        "source_fields": [
            "total_hldr_eqy_inc_min_int",
            "total_hldr_eqy_exc_min_int",
        ],
    },
    "debt_to_equity": {
        "name": "负债权益比",
        "metric_type": "structure_ratio",
        "unit": "ratio",
        "formula": "total_liab / total_hldr_eqy_inc_min_int",
        "operation": "divide",
        "numerator": "total_liab",
        "denominator": "total_hldr_eqy_inc_min_int",
        "source_fields": ["total_liab", "total_hldr_eqy_inc_min_int"],
    },

    # ========================================================
    # yoy：关键科目同比增长率
    # ========================================================
    "total_assets_yoy": {
        "name": "总资产同比增长率",
        "metric_type": "yoy",
        "unit": "ratio",
        "formula": "(cur.total_assets - base.total_assets) / base.total_assets",
        "field": "total_assets",
        "source_fields": ["total_assets"],
    },
    "total_liab_yoy": {
        "name": "总负债同比增长率",
        "metric_type": "yoy",
        "unit": "ratio",
        "formula": "(cur.total_liab - base.total_liab) / base.total_liab",
        "field": "total_liab",
        "source_fields": ["total_liab"],
    },
    "total_equity_yoy": {
        "name": "股东权益同比增长率",
        "metric_type": "yoy",
        "unit": "ratio",
        "formula": "(cur.total_hldr_eqy_inc_min_int - base.total_hldr_eqy_inc_min_int) / base.total_hldr_eqy_inc_min_int",
        "field": "total_hldr_eqy_inc_min_int",
        "source_fields": ["total_hldr_eqy_inc_min_int"],
    },
    "money_cap_yoy": {
        "name": "货币资金同比增长率",
        "metric_type": "yoy",
        "unit": "ratio",
        "formula": "(cur.money_cap - base.money_cap) / base.money_cap",
        "field": "money_cap",
        "source_fields": ["money_cap"],
    },
    "accounts_receiv_yoy": {
        "name": "应收账款同比增长率",
        "metric_type": "yoy",
        "unit": "ratio",
        "formula": "(cur.accounts_receiv - base.accounts_receiv) / base.accounts_receiv",
        "field": "accounts_receiv",
        "source_fields": ["accounts_receiv"],
    },
    "inventories_yoy": {
        "name": "存货同比增长率",
        "metric_type": "yoy",
        "unit": "ratio",
        "formula": "(cur.inventories - base.inventories) / base.inventories",
        "field": "inventories",
        "source_fields": ["inventories"],
    },
    "total_cur_assets_yoy": {
        "name": "流动资产同比增长率",
        "metric_type": "yoy",
        "unit": "ratio",
        "formula": "(cur.total_cur_assets - base.total_cur_assets) / base.total_cur_assets",
        "field": "total_cur_assets",
        "source_fields": ["total_cur_assets"],
    },
    "total_cur_liab_yoy": {
        "name": "流动负债同比增长率",
        "metric_type": "yoy",
        "unit": "ratio",
        "formula": "(cur.total_cur_liab - base.total_cur_liab) / base.total_cur_liab",
        "field": "total_cur_liab",
        "source_fields": ["total_cur_liab"],
    },
    "short_term_borr_yoy": {
        "name": "短期借款同比增长率",
        "metric_type": "yoy",
        "unit": "ratio",
        "formula": "(cur.short_term_borr - base.short_term_borr) / base.short_term_borr",
        "field": "short_term_borr",
        "source_fields": ["short_term_borr"],
    },
    "acct_payable_yoy": {
        "name": "应付账款同比增长率",
        "metric_type": "yoy",
        "unit": "ratio",
        "formula": "(cur.acct_payable - base.acct_payable) / base.acct_payable",
        "field": "acct_payable",
        "source_fields": ["acct_payable"],
    },

    # ========================================================
    # growth_spread：增速差
    # ========================================================
    "total_liab_yoy_minus_total_assets_yoy": {
        "name": "总负债同比增速减总资产同比增速",
        "metric_type": "growth_spread",
        "unit": "ratio",
        "formula": "total_liab_yoy - total_assets_yoy",
        "depends_on": ["total_liab_yoy", "total_assets_yoy"],
        "source_fields": ["total_liab", "total_assets"],
    },
    "accounts_receiv_yoy_minus_total_assets_yoy": {
        "name": "应收账款同比增速减总资产同比增速",
        "metric_type": "growth_spread",
        "unit": "ratio",
        "formula": "accounts_receiv_yoy - total_assets_yoy",
        "depends_on": ["accounts_receiv_yoy", "total_assets_yoy"],
        "source_fields": ["accounts_receiv", "total_assets"],
    },
    "inventories_yoy_minus_total_assets_yoy": {
        "name": "存货同比增速减总资产同比增速",
        "metric_type": "growth_spread",
        "unit": "ratio",
        "formula": "inventories_yoy - total_assets_yoy",
        "depends_on": ["inventories_yoy", "total_assets_yoy"],
        "source_fields": ["inventories", "total_assets"],
    },
    "current_liab_yoy_minus_total_liab_yoy": {
        "name": "流动负债同比增速减总负债同比增速",
        "metric_type": "growth_spread",
        "unit": "ratio",
        "formula": "total_cur_liab_yoy - total_liab_yoy",
        "depends_on": ["total_cur_liab_yoy", "total_liab_yoy"],
        "source_fields": ["total_cur_liab", "total_liab"],
    },
}