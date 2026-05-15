# ============================================================
# 1. 暴露给大模型选择的 metric_groups
# ============================================================

INCOME_METRIC_GROUPS: dict[str, list[str]] = {
    # 收入增长证据
    "income_growth": [
        "revenue_yoy",
        "total_revenue_yoy",
        "revenue_yoy_change",
        "total_revenue_yoy_change",
        "revenue_cagr",
        "total_revenue_cagr",
    ],

    # 利润增长证据
    "profit_growth": [
        "operate_profit_yoy",
        "total_profit_yoy",
        "net_profit_yoy",
        "parent_net_profit_yoy",
        "operate_profit_yoy_change",
        "total_profit_yoy_change",
        "net_profit_yoy_change",
        "parent_net_profit_yoy_change",
        "net_profit_cagr",
        "parent_net_profit_cagr",
        "basic_eps_yoy",
        "diluted_eps_yoy",
    ],

    # 成本费用变化证据
    "cost_expense_change": [
        "oper_cost_yoy",
        "total_cogs_yoy",
        "period_expense",
        "period_expense_yoy",
        "period_expense_yoy_change",
        "sell_exp_yoy",
        "admin_exp_yoy",
        "fin_exp_yoy",
        "sell_exp_yoy_change",
        "admin_exp_yoy_change",
        "fin_exp_yoy_change",
    ],

    # 增速差证据
    "growth_spread": [
        "net_profit_yoy_minus_revenue_yoy",
        "parent_net_profit_yoy_minus_revenue_yoy",
        "operate_profit_yoy_minus_revenue_yoy",
        "oper_cost_yoy_minus_revenue_yoy",
        "period_expense_yoy_minus_revenue_yoy",
    ],

    # 利润结构证据
    "profit_structure": [
        "gross_profit",
        "period_expense",
        "total_profit_minus_operating_profit",
        "total_profit_minus_net_profit",
        "net_profit_minus_parent_net_profit",
        "comprehensive_income_minus_parent_net_profit",
        "invest_income_to_total_profit",
        "invest_income_to_net_profit",
        "assets_impair_loss_to_total_profit",
        "assets_impair_loss_to_net_profit",
        "income_tax_to_total_profit",
        "minority_gain_to_net_profit",
        "parent_net_profit_to_net_profit",
        "operating_profit_to_total_profit",
        "net_profit_to_total_profit",
        "period_expense_to_gross_profit",
    ],

    # EPS 变化证据
    "eps_change": [
        "basic_eps_yoy",
        "diluted_eps_yoy",
        "basic_eps_yoy_change",
        "diluted_eps_yoy_change",
        "basic_eps_minus_diluted_eps",
        "basic_eps_cagr",
    ],
}

BALANCE_SHEET_METRIC_GROUPS: dict[str, list[str]] = {
    # 资产结构证据
    "asset_structure": [
        "cash_and_trading_assets",
        "cash_and_trading_assets_to_total_assets",
        "money_cap_to_total_assets",
        "current_assets_to_total_assets",
        "noncurrent_assets_to_total_assets",
        "fixed_assets_to_total_assets",
    ],

    # 流动资产结构证据
    "current_asset_structure": [
        "receivables_total",
        "receivables_total_to_current_assets",
        "accounts_receiv_to_current_assets",
        "inventory_to_current_assets",
        "prepayment_to_current_assets",
        "money_cap_to_current_assets",
    ],

    # 负债结构证据
    "liability_structure": [
        "current_liab_to_total_liab",
        "noncurrent_liab_to_total_liab",
        "short_term_borr_to_total_liab",
        "bond_payable_to_total_liab",
        "payables_total",
        "payables_total_to_total_liab",
    ],

    # 权益结构证据
    "equity_structure": [
        "minority_equity",
        "parent_equity_to_total_equity",
        "minority_equity_to_total_equity",
        "debt_to_equity",
    ],

    # 关键资产负债科目同比变化证据
    "balance_sheet_growth": [
        "total_assets_yoy",
        "total_liab_yoy",
        "total_equity_yoy",
        "money_cap_yoy",
        "accounts_receiv_yoy",
        "inventories_yoy",
        "total_cur_assets_yoy",
        "total_cur_liab_yoy",
        "short_term_borr_yoy",
        "acct_payable_yoy",
    ],

    # 增速差证据
    "balance_growth_spread": [
        "total_liab_yoy_minus_total_assets_yoy",
        "accounts_receiv_yoy_minus_total_assets_yoy",
        "inventories_yoy_minus_total_assets_yoy",
        "current_liab_yoy_minus_total_liab_yoy",
    ],
}

