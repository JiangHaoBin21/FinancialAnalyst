# ============================================================
# 2. tool 内部使用的 metric registry
#    大模型不需要知道这些 metric_code
# ============================================================
from typing import Any


# ---------------- INCOME METRICS --------------------
INCOME_METRIC_REGISTRY = {
    # =========================================================
    # 1. 收入与利润层级 profit_scale_layers
    # =========================================================
    "total_revenue_amount": {
        "name": "营业总收入",
        "group": "profit_scale_layers",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "total_revenue",
        "depends_on": ["total_revenue"],
        "description": "公司利润表口径下的营业总收入金额。",
        "interpretation": "用于观察整体收入规模变化。一般工商企业中，营业总收入和营业收入通常接近，但仍建议保留两者口径。",
        "higher_is_better": True,
        "priority": 1,
    },

    "revenue_amount": {
        "name": "营业收入",
        "group": "profit_scale_layers",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "revenue",
        "depends_on": ["revenue"],
        "description": "公司主营经营活动形成的营业收入金额。",
        "interpretation": "用于观察主营收入规模变化，并可与现金流销售收现、应收类资产变化联动分析收入质量。",
        "higher_is_better": True,
        "priority": 2,
    },

    "operating_profit_amount": {
        "name": "营业利润",
        "group": "profit_scale_layers",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "operate_profit",
        "depends_on": ["operate_profit"],
        "description": "公司日常经营及相关收益形成的营业利润。",
        "interpretation": "用于观察收入扣除成本费用及相关收益后的利润表现。",
        "higher_is_better": True,
        "priority": 3,
    },

    "total_profit_amount": {
        "name": "利润总额",
        "group": "profit_scale_layers",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "total_profit",
        "depends_on": ["total_profit"],
        "description": "营业利润加减营业外收支后的利润总额。",
        "interpretation": "用于观察税前利润规模，和营业利润对比可识别营业外因素影响。",
        "higher_is_better": True,
        "priority": 4,
    },

    "net_income_amount": {
        "name": "净利润",
        "group": "profit_scale_layers",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "n_income",
        "depends_on": ["n_income"],
        "description": "包含少数股东损益的净利润金额。",
        "interpretation": "用于观察公司整体净利润规模。归属于母公司股东的部分应查看 profit_attribution group。",
        "higher_is_better": True,
        "priority": 5,
    },

    # =========================================================
    # 2. 成本与期间费用金额 cost_expense_amounts
    # =========================================================
    "operating_cost_amount": {
        "name": "营业成本",
        "group": "cost_expense_amounts",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "oper_cost",
        "depends_on": ["oper_cost"],
        "description": "与营业收入直接对应的营业成本金额。",
        "interpretation": "用于观察成本规模变化；成本率等比率指标应由 fina_indicator tool 提供。",
        "higher_is_better": False,
        "priority": 1,
    },

    "total_cogs_amount": {
        "name": "营业总成本",
        "group": "cost_expense_amounts",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "total_cogs",
        "depends_on": ["total_cogs"],
        "description": "利润表中的营业总成本金额。",
        "interpretation": "用于观察成本费用整体压力；营业总成本率等标准比率应由 fina_indicator tool 提供。",
        "higher_is_better": False,
        "priority": 2,
    },

    "selling_expense_amount": {
        "name": "销售费用",
        "group": "cost_expense_amounts",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "sell_exp",
        "depends_on": ["sell_exp"],
        "description": "销售推广、渠道、市场等相关费用金额。",
        "interpretation": "用于观察销售投入是否扩张；销售费用率应由 fina_indicator tool 提供。",
        "higher_is_better": None,
        "priority": 3,
    },

    "admin_expense_amount": {
        "name": "管理费用",
        "group": "cost_expense_amounts",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "admin_exp",
        "depends_on": ["admin_exp"],
        "description": "公司管理活动相关费用金额。",
        "interpretation": "用于观察管理费用规模变化；管理费用率应由 fina_indicator tool 提供。",
        "higher_is_better": None,
        "priority": 4,
    },

    "tax_surcharge_amount": {
        "name": "税金及附加",
        "group": "cost_expense_amounts",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "biz_tax_surchg",
        "depends_on": ["biz_tax_surchg"],
        "description": "营业税金及附加金额。",
        "interpretation": "用于补充成本费用结构，观察税费附加对利润表的影响。",
        "higher_is_better": False,
        "priority": 5,
    },

    # =========================================================
    # 3. 研发投入与财务费用拆解 rd_and_finance_detail
    # =========================================================
    "rd_expense_amount": {
        "name": "研发费用",
        "group": "rd_and_finance_detail",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "rd_exp",
        "depends_on": ["rd_exp"],
        "description": "公司费用化研发投入金额。",
        "interpretation": "用于观察公司是否加大研发投入，尤其适合科技、制造、新能源等行业分析。",
        "higher_is_better": None,
        "priority": 1,
    },

    "finance_expense_amount": {
        "name": "财务费用",
        "group": "rd_and_finance_detail",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "fin_exp",
        "depends_on": ["fin_exp"],
        "description": "利润表中的财务费用净额。",
        "interpretation": "用于观察融资成本、汇兑、利息收支等综合影响；需结合利息费用和利息收入拆解。",
        "higher_is_better": False,
        "priority": 2,
    },

    "interest_expense_amount": {
        "name": "利息费用",
        "group": "rd_and_finance_detail",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "fin_exp_int_exp",
        "depends_on": ["fin_exp_int_exp"],
        "description": "财务费用中的利息费用。",
        "interpretation": "用于观察有息负债带来的融资成本压力，应结合 balance_sheet 的债务期限结构分析。",
        "higher_is_better": False,
        "priority": 3,
    },

    "interest_income_amount": {
        "name": "利息收入",
        "group": "rd_and_finance_detail",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "fin_exp_int_inc",
        "depends_on": ["fin_exp_int_inc"],
        "description": "财务费用中的利息收入。",
        "interpretation": "用于观察货币资金或理财等带来的利息收入，可能抵减部分财务费用压力。",
        "higher_is_better": True,
        "priority": 4,
    },

    "net_interest_expense_amount": {
        "name": "净利息费用",
        "group": "rd_and_finance_detail",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "fin_exp_int_exp - fin_exp_int_inc",
        "depends_on": ["fin_exp_int_exp", "fin_exp_int_inc"],
        "description": "利息费用扣除利息收入后的净利息支出。",
        "interpretation": "用于观察真实利息负担。若净利息费用上升，需结合有息负债规模和现金储备分析。",
        "higher_is_better": False,
        "priority": 5,
    },

    # =========================================================
    # 4. 非主营损益与一次性收益 non_core_profit_sources
    # =========================================================
    "investment_income_amount": {
        "name": "投资收益",
        "group": "non_core_profit_sources",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "invest_income",
        "depends_on": ["invest_income"],
        "description": "投资相关收益金额。",
        "interpretation": "投资收益占比较高时，需要判断利润是否过度依赖非主营投资回报。",
        "higher_is_better": None,
        "priority": 1,
    },

    "fair_value_change_gain_amount": {
        "name": "公允价值变动净收益",
        "group": "non_core_profit_sources",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "fv_value_chg_gain",
        "depends_on": ["fv_value_chg_gain"],
        "description": "公允价值变动产生的净收益或损失。",
        "interpretation": "波动性较强，通常持续性弱于主营经营利润。",
        "higher_is_better": None,
        "priority": 2,
    },

    "other_income_amount": {
        "name": "其他收益",
        "group": "non_core_profit_sources",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "oth_income",
        "depends_on": ["oth_income"],
        "description": "其他收益金额，常见来源包括政府补助等。",
        "interpretation": "其他收益较高时，需要关注利润对补助或非主营项目的依赖。",
        "higher_is_better": None,
        "priority": 3,
    },

    "asset_disposal_income_amount": {
        "name": "资产处置收益",
        "group": "non_core_profit_sources",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "asset_disp_income",
        "depends_on": ["asset_disp_income"],
        "description": "资产处置形成的收益或损失。",
        "interpretation": "资产处置收益通常不具备高度持续性，需和主营利润区分。",
        "higher_is_better": None,
        "priority": 4,
    },

    "net_non_operating_income_amount": {
        "name": "营业外收支净额",
        "group": "non_core_profit_sources",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "non_oper_income - non_oper_exp",
        "depends_on": ["non_oper_income", "non_oper_exp"],
        "description": "营业外收入扣除营业外支出后的净额。",
        "interpretation": "用于解释营业利润和利润总额之间的差异。",
        "higher_is_better": None,
        "priority": 5,
    },

    "non_core_profit_total_amount": {
        "name": "非主营损益合计",
        "group": "non_core_profit_sources",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "invest_income + fv_value_chg_gain + oth_income + asset_disp_income + non_oper_income - non_oper_exp",
        "depends_on": [
            "invest_income",
            "fv_value_chg_gain",
            "oth_income",
            "asset_disp_income",
            "non_oper_income",
            "non_oper_exp",
        ],
        "description": "投资收益、公允价值变动、其他收益、资产处置收益和营业外收支的合计影响。",
        "interpretation": "用于粗略衡量利润中来自非主营或低持续性项目的贡献。",
        "higher_is_better": None,
        "priority": 6,
    },

    "non_core_profit_to_total_profit": {
        "name": "非主营损益/利润总额",
        "group": "non_core_profit_sources",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "non_core_profit_total / total_profit",
        "depends_on": ["non_core_profit_total_amount", "total_profit"],
        "description": "衡量非主营损益相对利润总额的占比。",
        "interpretation": "比例较高时，说明利润可能较依赖非主营或一次性项目，应进一步查看扣非净利润。",
        "higher_is_better": False,
        "priority": 7,
    },

    # =========================================================
    # 5. 减值损失 impairment_losses
    # =========================================================
    "asset_impairment_loss_amount": {
        "name": "资产减值损失",
        "group": "impairment_losses",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "assets_impair_loss",
        "depends_on": ["assets_impair_loss"],
        "description": "资产减值损失金额。",
        "interpretation": "用于观察存货、商誉、固定资产等资产减值对利润的影响。",
        "higher_is_better": False,
        "priority": 1,
    },

    "credit_impairment_loss_amount": {
        "name": "信用减值损失",
        "group": "impairment_losses",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "credit_impa_loss",
        "depends_on": ["credit_impa_loss"],
        "description": "信用减值损失金额。",
        "interpretation": "常与应收账款、合同资产、其他应收款等信用风险相关，应结合 balance_sheet 的应收类资产分析。",
        "higher_is_better": False,
        "priority": 2,
    },

    "other_asset_impairment_loss_amount": {
        "name": "其他资产减值损失",
        "group": "impairment_losses",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "oth_impair_loss_assets",
        "depends_on": ["oth_impair_loss_assets"],
        "description": "其他资产减值损失金额。",
        "interpretation": "用于补充观察资产质量风险对利润表的影响。",
        "higher_is_better": False,
        "priority": 3,
    },

    "total_impairment_loss_amount": {
        "name": "减值损失合计",
        "group": "impairment_losses",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "assets_impair_loss + credit_impa_loss + oth_impair_loss_assets",
        "depends_on": [
            "assets_impair_loss",
            "credit_impa_loss",
            "oth_impair_loss_assets",
        ],
        "description": "资产减值、信用减值和其他资产减值的合计金额。",
        "interpretation": "用于衡量减值事项对利润表的综合拖累。",
        "higher_is_better": False,
        "priority": 4,
    },

    "impairment_to_operating_profit": {
        "name": "减值损失/营业利润",
        "group": "impairment_losses",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "total_impairment_loss / operate_profit",
        "depends_on": ["total_impairment_loss_amount", "operate_profit"],
        "description": "衡量减值损失相对营业利润的影响程度。",
        "interpretation": "比例较高时，说明利润受到减值明显影响，需要结合资产质量进一步分析。",
        "higher_is_better": False,
        "priority": 5,
    },

    # =========================================================
    # 6. 归母与少数股东损益 profit_attribution
    # =========================================================
    "parent_net_income_amount": {
        "name": "归母净利润",
        "group": "profit_attribution",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "n_income_attr_p",
        "depends_on": ["n_income_attr_p"],
        "description": "归属于母公司股东的净利润金额。",
        "interpretation": "相比整体净利润，更能反映归属于上市公司股东的利润。",
        "higher_is_better": True,
        "priority": 1,
    },

    "minority_gain_amount": {
        "name": "少数股东损益",
        "group": "profit_attribution",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "minority_gain",
        "depends_on": ["minority_gain"],
        "description": "归属于少数股东的损益金额。",
        "interpretation": "少数股东损益较高时，整体净利润和归母净利润可能出现差异。",
        "higher_is_better": None,
        "priority": 2,
    },

    "parent_net_income_share": {
        "name": "归母净利润/净利润",
        "group": "profit_attribution",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "n_income_attr_p / n_income",
        "depends_on": ["n_income_attr_p", "n_income"],
        "description": "衡量整体净利润中归属于母公司股东的比例。",
        "interpretation": "比例较低时，说明较大部分利润归属于少数股东，需关注股东收益归属。",
        "higher_is_better": True,
        "priority": 3,
    },

    "minority_gain_share": {
        "name": "少数股东损益/净利润",
        "group": "profit_attribution",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "minority_gain / n_income",
        "depends_on": ["minority_gain", "n_income"],
        "description": "衡量整体净利润中少数股东损益占比。",
        "interpretation": "比例较高时，说明上市公司股东实际享有的利润可能低于整体净利润表现。",
        "higher_is_better": False,
        "priority": 4,
    },

    # =========================================================
    # 7. 其他综合收益与综合收益 comprehensive_income
    # =========================================================
    "other_comprehensive_income_amount": {
        "name": "其他综合收益",
        "group": "comprehensive_income",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "oth_compr_income",
        "depends_on": ["oth_compr_income"],
        "description": "未计入当期损益但计入综合收益的项目金额。",
        "interpretation": "用于观察是否存在影响权益但未进入净利润的收益或损失。",
        "higher_is_better": None,
        "priority": 1,
    },

    "parent_comprehensive_income_amount": {
        "name": "归母综合收益总额",
        "group": "comprehensive_income",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "compr_inc_attr_p",
        "depends_on": ["compr_inc_attr_p"],
        "description": "归属于母公司股东的综合收益总额。",
        "interpretation": "用于从综合收益角度观察归母股东权益变动。",
        "higher_is_better": True,
        "priority": 2,
    },

    "comprehensive_income_gap_amount": {
        "name": "归母综合收益与归母净利润差额",
        "group": "comprehensive_income",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "compr_inc_attr_p - n_income_attr_p",
        "depends_on": ["compr_inc_attr_p", "n_income_attr_p"],
        "description": "归母综合收益总额与归母净利润之间的差额。",
        "interpretation": "差额较大时，说明其他综合收益对归母股东收益表现有明显影响。",
        "higher_is_better": None,
        "priority": 3,
    },

    "comprehensive_income_gap_to_parent_net_income": {
        "name": "综合收益差额/归母净利润",
        "group": "comprehensive_income",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "(compr_inc_attr_p - n_income_attr_p) / n_income_attr_p",
        "depends_on": ["compr_inc_attr_p", "n_income_attr_p"],
        "description": "衡量归母综合收益与归母净利润差额相对归母净利润的比例。",
        "interpretation": "比例绝对值较高时，说明净利润以外的综合收益项目对股东收益表现影响较大。",
        "higher_is_better": None,
        "priority": 4,
    },
}

# ---------------- BALANCE METRICS ------------------
BALANCE_SHEET_METRIC_REGISTRY = {
    # =========================================================
    # 1. 资产规模与资产结构 asset_scale_structure
    # =========================================================
    "current_asset_ratio": {
        "name": "流动资产占比",
        "group": "asset_scale_structure",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "total_cur_assets / total_assets",
        "depends_on": ["total_cur_assets", "total_assets"],
        "description": "衡量流动资产在总资产中的占比。",
        "interpretation": "占比高通常说明资产流动性较强，但要结合存货、应收等资产质量判断。",
        "higher_is_better": None,
        "priority": 1,
    },

    "noncurrent_asset_ratio": {
        "name": "非流动资产占比",
        "group": "asset_scale_structure",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "total_nca / total_assets",
        "depends_on": ["total_nca", "total_assets"],
        "description": "衡量非流动资产在总资产中的占比。",
        "interpretation": "占比高可能说明公司偏重资产，也可能意味着长期资产沉淀较多。",
        "higher_is_better": None,
        "priority": 2,
    },

    "fixed_asset_ratio": {
        "name": "固定资产占比",
        "group": "asset_scale_structure",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "effective_fixed_assets / total_assets",
        "depends_on": ["fix_assets", "fix_assets_total", "total_assets"],
        "description": "衡量固定资产在总资产中的占比。",
        "interpretation": "用于判断公司轻资产或重资产属性。",
        "higher_is_better": None,
        "priority": 3,
    },

    "cash_asset_ratio": {
        "name": "货币资金占比",
        "group": "asset_scale_structure",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "money_cap / total_assets",
        "depends_on": ["money_cap", "total_assets"],
        "description": "衡量货币资金在总资产中的占比。",
        "interpretation": "占比高通常说明现金储备较充足，但也可能意味着资金使用效率偏低。",
        "higher_is_better": None,
        "priority": 4,
    },

    # =========================================================
    # 2. 债务期限结构与短债压力 debt_maturity_structure
    # =========================================================
    "short_term_interest_debt": {
        "name": "短期有息负债",
        "group": "debt_maturity_structure",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "st_borr + non_cur_liab_due_1y + st_bonds_payable",
        "depends_on": ["st_borr", "non_cur_liab_due_1y", "st_bonds_payable"],
        "description": "衡量短期内需要偿还或滚续的有息债务规模。",
        "interpretation": "短期有息负债越高，越需要关注现金覆盖能力和再融资压力。",
        "higher_is_better": False,
        "priority": 1,
    },

    "long_term_interest_debt": {
        "name": "长期有息负债",
        "group": "debt_maturity_structure",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "lt_borr + bond_payable + lease_liab",
        "depends_on": ["lt_borr", "bond_payable", "lease_liab"],
        "description": "衡量长期有息债务规模。",
        "interpretation": "长期有息负债较高不一定代表短期风险，但会影响长期资本结构和利息负担。",
        "higher_is_better": None,
        "priority": 2,
    },

    "debt_maturity_pressure": {
        "name": "短债占有息负债比例",
        "group": "debt_maturity_structure",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "short_term_interest_debt / interest_bearing_debt",
        "depends_on": ["short_term_interest_debt", "interest_bearing_debt"],
        "description": "衡量有息债务中短期债务的占比。",
        "interpretation": "比例越高，通常说明债务期限结构越短，短期滚续压力越大。",
        "higher_is_better": False,
        "priority": 3,
    },

    "cash_to_short_debt": {
        "name": "现金短债比",
        "group": "debt_maturity_structure",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "money_cap / short_term_interest_debt",
        "depends_on": ["money_cap", "short_term_interest_debt"],
        "description": "衡量货币资金对短期有息负债的覆盖能力。",
        "interpretation": "比例越高，短期有息债务的现金覆盖越充分。",
        "higher_is_better": True,
        "priority": 4,
    },

    # =========================================================
    # 3. 应收、存货与经营占款 receivables_inventory
    # =========================================================
    "operating_receivables": {
        "name": "经营性应收合计",
        "group": "receivables_inventory",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "effective_receivables + contract_assets",
        "depends_on": [
            "notes_receiv",
            "accounts_receiv",
            "accounts_receiv_bill",
            "contract_assets",
        ],
        "description": "衡量应收票据、应收账款、合同资产等经营性应收项目的合计规模。",
        "interpretation": "如果增长显著快于收入增长，可能提示收入质量或回款压力。",
        "higher_is_better": False,
        "priority": 1,
    },

    "receivable_asset_ratio": {
        "name": "经营性应收占总资产比例",
        "group": "receivables_inventory",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "operating_receivables / total_assets",
        "depends_on": ["operating_receivables", "total_assets"],
        "description": "衡量经营性应收项目对总资产的占用比例。",
        "interpretation": "比例越高，说明资产中被客户或合同资产占用的部分越多。",
        "higher_is_better": False,
        "priority": 2,
    },

    "inventory_asset_ratio": {
        "name": "存货占总资产比例",
        "group": "receivables_inventory",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "inventories / total_assets",
        "depends_on": ["inventories", "total_assets"],
        "description": "衡量存货在总资产中的占比。",
        "interpretation": "比例异常上升可能提示库存压力，需要结合收入和成本变化判断。",
        "higher_is_better": None,
        "priority": 3,
    },

    "receivable_inventory_ratio": {
        "name": "经营性应收与存货占总资产比例",
        "group": "receivables_inventory",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "(operating_receivables + inventories) / total_assets",
        "depends_on": ["operating_receivables", "inventories", "total_assets"],
        "description": "衡量应收和存货对资产的综合占用程度。",
        "interpretation": "比例越高，通常说明经营性资产占用越重。",
        "higher_is_better": False,
        "priority": 4,
    },

    "contract_asset_ratio": {
        "name": "合同资产占总资产比例",
        "group": "receivables_inventory",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "contract_assets / total_assets",
        "depends_on": ["contract_assets", "total_assets"],
        "description": "衡量合同资产在总资产中的占比。",
        "interpretation": "合同资产占比上升可能与收入确认、项目结算周期有关。",
        "higher_is_better": None,
        "priority": 5,
    },

    # =========================================================
    # 4. 应付、预收与合同负债 payables_contract_liability
    # =========================================================
    "operating_payables": {
        "name": "经营性应付合计",
        "group": "payables_contract_liability",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "effective_payables + adv_receipts + contract_liab",
        "depends_on": [
            "notes_payable",
            "acct_payable",
            "accounts_pay",
            "adv_receipts",
            "contract_liab",
        ],
        "description": "衡量应付票据、应付账款、预收款项、合同负债等经营性资金来源。",
        "interpretation": "经营性应付较高可能说明公司对供应商或客户占款能力较强。",
        "higher_is_better": None,
        "priority": 1,
    },

    "payable_liability_ratio": {
        "name": "经营性应付占总负债比例",
        "group": "payables_contract_liability",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "operating_payables / total_liab",
        "depends_on": ["operating_payables", "total_liab"],
        "description": "衡量负债中经营性应付项目的占比。",
        "interpretation": "比例较高说明负债更多来自经营性占款，而不完全来自金融债务。",
        "higher_is_better": None,
        "priority": 2,
    },

    "advance_contract_liab_ratio": {
        "name": "预收与合同负债占总资产比例",
        "group": "payables_contract_liability",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "(adv_receipts + contract_liab) / total_assets",
        "depends_on": ["adv_receipts", "contract_liab", "total_assets"],
        "description": "衡量预收款项和合同负债对公司资金来源的贡献。",
        "interpretation": "比例较高通常说明公司从客户处提前获得资金的能力较强。",
        "higher_is_better": None,
        "priority": 3,
    },

    "net_operating_working_capital": {
        "name": "净经营营运资本",
        "group": "payables_contract_liability",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "operating_receivables + inventories - operating_payables",
        "depends_on": [
            "operating_receivables",
            "inventories",
            "operating_payables",
        ],
        "description": "衡量经营环节实际占用的营运资金。",
        "interpretation": "数值越高，通常说明经营环节占用资金越多。",
        "higher_is_better": False,
        "priority": 4,
    },

    # =========================================================
    # 5. 商誉与无形资产风险 soft_asset_risk
    # =========================================================
    "goodwill_asset_ratio": {
        "name": "商誉占总资产比例",
        "group": "soft_asset_risk",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "goodwill / total_assets",
        "depends_on": ["goodwill", "total_assets"],
        "description": "衡量商誉在总资产中的占比。",
        "interpretation": "占比越高，越需要关注并购形成商誉的后续减值风险。",
        "higher_is_better": False,
        "priority": 1,
    },

    "intangible_asset_ratio": {
        "name": "无形资产占总资产比例",
        "group": "soft_asset_risk",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "intan_assets / total_assets",
        "depends_on": ["intan_assets", "total_assets"],
        "description": "衡量无形资产在总资产中的占比。",
        "interpretation": "占比高不一定是风险，但需要结合行业属性、研发资本化和摊销政策判断。",
        "higher_is_better": None,
        "priority": 2,
    },

    "goodwill_intangible_ratio": {
        "name": "商誉和无形资产占总资产比例",
        "group": "soft_asset_risk",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "(goodwill + intan_assets) / total_assets",
        "depends_on": ["goodwill", "intan_assets", "total_assets"],
        "description": "衡量商誉和无形资产等偏软性资产在总资产中的占比。",
        "interpretation": "比例越高，越需要关注资产质量、减值风险和利润质量。",
        "higher_is_better": False,
        "priority": 3,
    },

    # =========================================================
    # 6. 在建工程与扩产风险 construction_asset_risk
    # =========================================================
    "cip_asset_ratio": {
        "name": "在建工程占总资产比例",
        "group": "construction_asset_risk",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "effective_cip / total_assets",
        "depends_on": ["cip_total", "total_assets"],
        "description": "衡量在建工程对总资产的占用程度。",
        "interpretation": "比例较高可能说明公司处于扩产或项目建设期。",
        "higher_is_better": None,
        "priority": 1,
    },

    "cip_fixed_asset_ratio": {
        "name": "在建工程占固定资产比例",
        "group": "construction_asset_risk",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "effective_cip / effective_fixed_assets",
        "depends_on": ["cip_total", "fix_assets", "fix_assets_total"],
        "description": "衡量在建工程相对于固定资产规模的比例。",
        "interpretation": "比例较高说明在建项目规模较大，需要关注转固节奏、产能消化和资本开支压力。",
        "higher_is_better": None,
        "priority": 2,
    },
}


CASHFLOW_METRIC_REGISTRY = {
    # =========================================================
    # 1. 经营现金流入结构 operating_cash_inflows
    # =========================================================
    "sales_cash_received": {
        "name": "销售商品、提供劳务收到的现金",
        "group": "operating_cash_inflows",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "c_fr_sale_sg",
        "depends_on": ["c_fr_sale_sg"],
        "description": "经营活动中来自销售商品、提供劳务的现金流入，是观察销售回款能力的核心字段。",
        "higher_is_better": True,
        "priority": 1,
    },

    "operating_cash_inflow_total": {
        "name": "经营活动现金流入小计",
        "group": "operating_cash_inflows",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "c_inf_fr_operate_a",
        "depends_on": ["c_inf_fr_operate_a"],
        "description": "经营活动产生的现金流入总额，用于观察经营现金流入规模。",
        "higher_is_better": True,
        "priority": 2,
    },

    "sales_cash_inflow_share": {
        "name": "销售收现占经营现金流入比例",
        "group": "operating_cash_inflows",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "c_fr_sale_sg / c_inf_fr_operate_a",
        "depends_on": ["c_fr_sale_sg", "c_inf_fr_operate_a"],
        "description": "衡量经营现金流入中销售回款的占比，用于判断经营现金流入是否主要来自主营销售。",
        "higher_is_better": True,
        "priority": 3,
    },

    "other_operating_inflow_share": {
        "name": "其他经营现金流入占比",
        "group": "operating_cash_inflows",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "c_fr_oth_operate_a / c_inf_fr_operate_a",
        "depends_on": ["c_fr_oth_operate_a", "c_inf_fr_operate_a"],
        "description": "衡量经营现金流入中其他经营现金流入的占比，占比异常高时需要关注经营现金流来源质量。",
        "higher_is_better": None,
        "priority": 4,
    },

    # =========================================================
    # 2. 经营现金流出结构 operating_cash_outflows
    # =========================================================
    "goods_services_cash_paid": {
        "name": "购买商品、接受劳务支付的现金",
        "group": "operating_cash_outflows",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "c_paid_goods_s",
        "depends_on": ["c_paid_goods_s"],
        "description": "经营活动中用于购买商品、接受劳务的现金支出，是经营现金流出中最核心的采购付款项。",
        "higher_is_better": False,
        "priority": 1,
    },

    "employee_cash_paid": {
        "name": "支付给职工以及为职工支付的现金",
        "group": "operating_cash_outflows",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "c_paid_to_for_empl",
        "depends_on": ["c_paid_to_for_empl"],
        "description": "经营活动中支付给职工以及为职工支付的现金，用于观察人工相关现金支出规模。",
        "higher_is_better": None,
        "priority": 2,
    },

    "taxes_cash_paid": {
        "name": "支付的各项税费",
        "group": "operating_cash_outflows",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "c_paid_for_taxes",
        "depends_on": ["c_paid_for_taxes"],
        "description": "经营活动中支付的各项税费现金支出。",
        "higher_is_better": False,
        "priority": 3,
    },

    "operating_cash_outflow_total": {
        "name": "经营活动现金流出小计",
        "group": "operating_cash_outflows",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "st_cash_out_act",
        "depends_on": ["st_cash_out_act"],
        "description": "经营活动产生的现金流出总额，用于观察经营现金支出规模。",
        "higher_is_better": False,
        "priority": 4,
    },

    "purchase_cash_outflow_share": {
        "name": "采购付款占经营现金流出比例",
        "group": "operating_cash_outflows",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "c_paid_goods_s / st_cash_out_act",
        "depends_on": ["c_paid_goods_s", "st_cash_out_act"],
        "description": "衡量经营现金流出中采购付款的占比，用于观察经营现金支出是否主要由采购付款驱动。",
        "higher_is_better": None,
        "priority": 5,
    },

    # =========================================================
    # 3. 经营现金流净额 operating_cash_net
    # =========================================================
    "operating_net_cashflow": {
        "name": "经营活动现金流量净额",
        "group": "operating_cash_net",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "n_cashflow_act",
        "depends_on": ["n_cashflow_act"],
        "description": "经营活动产生的现金流量净额，用于观察公司经营活动最终沉淀下来的现金。",
        "higher_is_better": True,
        "priority": 1,
    },

    "operating_cashflow_inflow_margin": {
        "name": "经营现金流净额/经营现金流入",
        "group": "operating_cash_net",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "n_cashflow_act / c_inf_fr_operate_a",
        "depends_on": ["n_cashflow_act", "c_inf_fr_operate_a"],
        "description": "衡量经营现金流入最终转化为经营现金流净额的比例，用于观察经营现金流沉淀能力。",
        "higher_is_better": True,
        "priority": 2,
    },

    # =========================================================
    # 4. 投资现金流与资本开支 investing_capex_structure
    # =========================================================
    "investment_cash_inflow_total": {
        "name": "投资活动现金流入小计",
        "group": "investing_capex_structure",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "stot_inflows_inv_act",
        "depends_on": ["stot_inflows_inv_act"],
        "description": "投资活动产生的现金流入总额。",
        "higher_is_better": None,
        "priority": 1,
    },

    "capex_cash_paid": {
        "name": "购建长期资产支付的现金",
        "group": "investing_capex_structure",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "c_pay_acq_const_fiolta",
        "depends_on": ["c_pay_acq_const_fiolta"],
        "description": "购建固定资产、无形资产和其他长期资产支付的现金，是观察资本开支和扩产强度的核心字段。",
        "higher_is_better": None,
        "priority": 2,
    },

    "investment_cash_paid": {
        "name": "投资支付的现金",
        "group": "investing_capex_structure",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "c_paid_invest",
        "depends_on": ["c_paid_invest"],
        "description": "投资活动中支付的投资现金，用于观察金融投资、股权投资等投资支出。",
        "higher_is_better": None,
        "priority": 3,
    },

    "investment_cash_outflow_total": {
        "name": "投资活动现金流出小计",
        "group": "investing_capex_structure",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "stot_out_inv_act",
        "depends_on": ["stot_out_inv_act"],
        "description": "投资活动产生的现金流出总额，用于观察投资现金支出规模。",
        "higher_is_better": False,
        "priority": 4,
    },

    "investing_net_cashflow": {
        "name": "投资活动现金流量净额",
        "group": "investing_capex_structure",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "n_cashflow_inv_act",
        "depends_on": ["n_cashflow_inv_act"],
        "description": "投资活动产生的现金流量净额，用于观察公司投资活动整体是净流入还是净流出。",
        "higher_is_better": None,
        "priority": 5,
    },

    "capex_outflow_share": {
        "name": "资本开支占投资现金流出比例",
        "group": "investing_capex_structure",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "c_pay_acq_const_fiolta / stot_out_inv_act",
        "depends_on": ["c_pay_acq_const_fiolta", "stot_out_inv_act"],
        "description": "衡量投资现金流出中有多少用于购建长期资产，用于判断投资净流出是否主要由扩产或长期资产投入驱动。",
        "higher_is_better": None,
        "priority": 6,
    },

    # =========================================================
    # 5. 筹资现金流结构 financing_cashflow_structure
    # =========================================================
    "equity_financing_cash_received": {
        "name": "吸收投资收到的现金",
        "group": "financing_cashflow_structure",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "c_recp_cap_contrib",
        "depends_on": ["c_recp_cap_contrib"],
        "description": "吸收投资收到的现金，用于观察股权融资现金流入。",
        "higher_is_better": None,
        "priority": 1,
    },

    "debt_financing_cash_received": {
        "name": "债务融资收到的现金",
        "group": "financing_cashflow_structure",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "c_recp_borrow + proc_issue_bonds",
        "depends_on": ["c_recp_borrow", "proc_issue_bonds"],
        "description": "取得借款收到的现金与发行债券收到的现金之和，用于观察债务融资现金流入。",
        "higher_is_better": None,
        "priority": 2,
    },

    "financing_cash_inflow_total": {
        "name": "筹资活动现金流入小计",
        "group": "financing_cashflow_structure",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "stot_cash_in_fnc_act",
        "depends_on": ["stot_cash_in_fnc_act"],
        "description": "筹资活动产生的现金流入总额，用于观察外部融资流入规模。",
        "higher_is_better": None,
        "priority": 3,
    },

    "debt_repayment_cash_paid": {
        "name": "偿还债务支付的现金",
        "group": "financing_cashflow_structure",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "c_prepay_amt_borr",
        "depends_on": ["c_prepay_amt_borr"],
        "description": "偿还债务支付的现金，用于观察债务偿还压力。",
        "higher_is_better": False,
        "priority": 4,
    },

    "dividend_interest_cash_paid": {
        "name": "分配股利、利润或偿付利息支付的现金",
        "group": "financing_cashflow_structure",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "c_pay_dist_dpcp_int_exp",
        "depends_on": ["c_pay_dist_dpcp_int_exp"],
        "description": "用于分配股利、利润或偿付利息的现金支出，用于观察分红和付息现金压力。",
        "higher_is_better": None,
        "priority": 5,
    },

    "financing_cash_outflow_total": {
        "name": "筹资活动现金流出小计",
        "group": "financing_cashflow_structure",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "stot_cashout_fnc_act",
        "depends_on": ["stot_cashout_fnc_act"],
        "description": "筹资活动产生的现金流出总额，用于观察偿债、分红付息及其他筹资现金流出规模。",
        "higher_is_better": False,
        "priority": 6,
    },

    "financing_net_cashflow": {
        "name": "筹资活动现金流量净额",
        "group": "financing_cashflow_structure",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "n_cash_flows_fnc_act",
        "depends_on": ["n_cash_flows_fnc_act"],
        "description": "筹资活动产生的现金流量净额，用于观察公司整体是融资流入还是融资流出。",
        "higher_is_better": None,
        "priority": 7,
    },

    # =========================================================
    # 6. 现金及现金等价物变化 cash_balance_change
    # =========================================================
    "beginning_cash_equivalent": {
        "name": "期初现金及现金等价物余额",
        "group": "cash_balance_change",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "c_cash_equ_beg_period",
        "depends_on": ["c_cash_equ_beg_period"],
        "description": "期初现金及现金等价物余额。",
        "higher_is_better": None,
        "priority": 1,
    },

    "ending_cash_equivalent": {
        "name": "期末现金及现金等价物余额",
        "group": "cash_balance_change",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "c_cash_equ_end_period",
        "depends_on": ["c_cash_equ_end_period"],
        "description": "期末现金及现金等价物余额。",
        "higher_is_better": True,
        "priority": 2,
    },

    "net_cash_equivalent_increase": {
        "name": "现金及现金等价物净增加额",
        "group": "cash_balance_change",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "n_incr_cash_cash_equ",
        "depends_on": ["n_incr_cash_cash_equ"],
        "description": "本期现金及现金等价物净增加额，用于观察现金余额的增减变化。",
        "higher_is_better": None,
        "priority": 3,
    },

    # =========================================================
    # 7. 经营现金流间接法调节 indirect_operating_reconciliation
    # =========================================================
    "indirect_net_profit_base": {
        "name": "间接法净利润基数",
        "group": "indirect_operating_reconciliation",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "net_profit",
        "depends_on": ["net_profit"],
        "description": "现金流量表间接法中用于调节经营现金流的净利润基数。",
        "higher_is_better": True,
        "priority": 1,
    },

    "depreciation_amortization_amount": {
        "name": "折旧摊销合计",
        "group": "indirect_operating_reconciliation",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "depr_fa_coga_dpba + amort_intang_assets",
        "depends_on": ["depr_fa_coga_dpba", "amort_intang_assets"],
        "description": "固定资产折旧等与无形资产摊销的合计，属于非现金费用调节项。",
        "higher_is_better": None,
        "priority": 2,
    },

    "inventory_decrease_cash_effect": {
        "name": "存货减少的现金流影响",
        "group": "indirect_operating_reconciliation",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "decr_inventories",
        "depends_on": ["decr_inventories"],
        "description": "存货减少对经营现金流的调节影响。若为正，通常表示存货释放现金流；若为负，可能表示存货占用现金流。",
        "higher_is_better": True,
        "priority": 3,
    },

    "operating_receivable_decrease_cash_effect": {
        "name": "经营性应收减少的现金流影响",
        "group": "indirect_operating_reconciliation",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "decr_oper_payable",
        "depends_on": ["decr_oper_payable"],
        "description": "经营性应收项目减少对经营现金流的调节影响。注意 TuShare 字段名为 decr_oper_payable，但描述为经营性应收项目的减少。",
        "higher_is_better": True,
        "priority": 4,
    },

    "operating_payable_increase_cash_effect": {
        "name": "经营性应付增加的现金流影响",
        "group": "indirect_operating_reconciliation",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "incr_oper_payable",
        "depends_on": ["incr_oper_payable"],
        "description": "经营性应付项目增加对经营现金流的调节影响。若为正，通常说明通过应付款增加释放经营现金流。",
        "higher_is_better": True,
        "priority": 5,
    },

    "indirect_operating_cashflow": {
        "name": "间接法经营现金流净额",
        "group": "indirect_operating_reconciliation",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "im_net_cashflow_oper_act",
        "depends_on": ["im_net_cashflow_oper_act"],
        "description": "现金流量表间接法披露的经营活动现金流量净额。",
        "higher_is_better": True,
        "priority": 6,
    },
}


FINA_INDICATOR_METRIC_REGISTRY = {
    # =========================================================
    # 1. 每股与股东价值指标 per_share_value
    # =========================================================
    "eps": {
        "name": "每股收益",
        "group": "per_share_value",
        "field_name": "eps",
        "metric_type": "per_share",
        "unit": "元/股",
        "description": "基本每股收益，用于观察普通股股东每股盈利能力。",
        "higher_is_better": True,
        "priority": 1,
    },

    "dt_eps": {
        "name": "稀释每股收益",
        "group": "per_share_value",
        "field_name": "dt_eps",
        "metric_type": "per_share",
        "unit": "元/股",
        "description": "稀释每股收益，用于观察潜在股本稀释后的每股盈利能力。",
        "higher_is_better": True,
        "priority": 2,
    },

    "bps": {
        "name": "每股净资产",
        "group": "per_share_value",
        "field_name": "bps",
        "metric_type": "per_share",
        "unit": "元/股",
        "description": "每股净资产，用于观察每股对应的账面净资产价值。",
        "higher_is_better": True,
        "priority": 3,
    },

    "ocfps": {
        "name": "每股经营现金流",
        "group": "per_share_value",
        "field_name": "ocfps",
        "metric_type": "per_share",
        "unit": "元/股",
        "description": "每股经营活动现金流量净额，用于观察每股经营现金创造能力。",
        "higher_is_better": True,
        "priority": 4,
    },

    "cfps": {
        "name": "每股现金流量净额",
        "group": "per_share_value",
        "field_name": "cfps",
        "metric_type": "per_share",
        "unit": "元/股",
        "description": "每股现金流量净额，用于观察每股整体现金增减情况。",
        "higher_is_better": True,
        "priority": 5,
    },

    "fcff_ps": {
        "name": "每股 FCFF",
        "group": "per_share_value",
        "field_name": "fcff_ps",
        "metric_type": "per_share",
        "unit": "元/股",
        "description": "每股企业自由现金流，用于观察企业层面每股自由现金流创造能力。",
        "higher_is_better": True,
        "priority": 6,
    },

    "fcfe_ps": {
        "name": "每股 FCFE",
        "group": "per_share_value",
        "field_name": "fcfe_ps",
        "metric_type": "per_share",
        "unit": "元/股",
        "description": "每股股权自由现金流，用于观察归属于股东口径的每股自由现金流。",
        "higher_is_better": True,
        "priority": 7,
    },

    # =========================================================
    # 2. 盈利能力与利润率 profitability_margin
    # =========================================================
    "grossprofit_margin": {
        "name": "销售毛利率",
        "group": "profitability_margin",
        "field_name": "grossprofit_margin",
        "metric_type": "percent",
        "unit": "%",
        "description": "销售毛利率，用于观察营业收入扣除营业成本后的盈利空间。",
        "higher_is_better": True,
        "priority": 1,
    },

    "netprofit_margin": {
        "name": "销售净利率",
        "group": "profitability_margin",
        "field_name": "netprofit_margin",
        "metric_type": "percent",
        "unit": "%",
        "description": "销售净利率，用于观察收入最终转化为净利润的能力。",
        "higher_is_better": True,
        "priority": 2,
    },

    "profit_to_gr": {
        "name": "净利润/营业总收入",
        "group": "profitability_margin",
        "field_name": "profit_to_gr",
        "metric_type": "percent",
        "unit": "%",
        "description": "净利润相对营业总收入的比例，用于观察整体净利水平。",
        "higher_is_better": True,
        "priority": 3,
    },

    "op_of_gr": {
        "name": "营业利润/营业总收入",
        "group": "profitability_margin",
        "field_name": "op_of_gr",
        "metric_type": "percent",
        "unit": "%",
        "description": "营业利润相对营业总收入的比例，用于观察经营利润率。",
        "higher_is_better": True,
        "priority": 4,
    },

    "ebit_of_gr": {
        "name": "EBIT/营业总收入",
        "group": "profitability_margin",
        "field_name": "ebit_of_gr",
        "metric_type": "percent",
        "unit": "%",
        "description": "EBIT 相对营业总收入的比例，用于观察息税前盈利能力。",
        "higher_is_better": True,
        "priority": 5,
    },

    # =========================================================
    # 3. 成本费用率 expense_cost_margin
    # =========================================================
    "cogs_of_sales": {
        "name": "销售成本率",
        "group": "expense_cost_margin",
        "field_name": "cogs_of_sales",
        "metric_type": "percent",
        "unit": "%",
        "description": "销售成本占销售收入的比例，用于观察成本压力。",
        "higher_is_better": False,
        "priority": 1,
    },

    "expense_of_sales": {
        "name": "销售期间费用率",
        "group": "expense_cost_margin",
        "field_name": "expense_of_sales",
        "metric_type": "percent",
        "unit": "%",
        "description": "期间费用占销售收入的比例，用于观察费用控制水平。",
        "higher_is_better": False,
        "priority": 2,
    },

    "saleexp_to_gr": {
        "name": "销售费用/营业总收入",
        "group": "expense_cost_margin",
        "field_name": "saleexp_to_gr",
        "metric_type": "percent",
        "unit": "%",
        "description": "销售费用相对营业总收入的比例，用于观察销售投入强度。",
        "higher_is_better": None,
        "priority": 3,
    },

    "adminexp_of_gr": {
        "name": "管理费用/营业总收入",
        "group": "expense_cost_margin",
        "field_name": "adminexp_of_gr",
        "metric_type": "percent",
        "unit": "%",
        "description": "管理费用相对营业总收入的比例，用于观察管理费用负担。",
        "higher_is_better": False,
        "priority": 4,
    },

    "finaexp_of_gr": {
        "name": "财务费用/营业总收入",
        "group": "expense_cost_margin",
        "field_name": "finaexp_of_gr",
        "metric_type": "percent",
        "unit": "%",
        "description": "财务费用相对营业总收入的比例，用于观察财务费用压力。",
        "higher_is_better": False,
        "priority": 5,
    },

    "impai_ttm": {
        "name": "资产减值损失/营业总收入",
        "group": "expense_cost_margin",
        "field_name": "impai_ttm",
        "metric_type": "percent",
        "unit": "%",
        "description": "资产减值损失相对营业总收入的比例，用于观察减值对收入和利润的侵蚀程度。",
        "higher_is_better": False,
        "priority": 6,
    },

    # =========================================================
    # 4. 资产与资本回报率 return_efficiency
    # =========================================================
    "roe": {
        "name": "净资产收益率 ROE",
        "group": "return_efficiency",
        "field_name": "roe",
        "metric_type": "percent",
        "unit": "%",
        "description": "净资产收益率，用于观察股东权益回报水平。",
        "higher_is_better": True,
        "priority": 1,
    },

    "roe_waa": {
        "name": "加权平均 ROE",
        "group": "return_efficiency",
        "field_name": "roe_waa",
        "metric_type": "percent",
        "unit": "%",
        "description": "加权平均净资产收益率，用于观察更常用的股东回报口径。",
        "higher_is_better": True,
        "priority": 2,
    },

    "roe_dt": {
        "name": "扣非后 ROE",
        "group": "return_efficiency",
        "field_name": "roe_dt",
        "metric_type": "percent",
        "unit": "%",
        "description": "扣除非经常损益后的 ROE，用于观察更可持续的股东回报能力。",
        "higher_is_better": True,
        "priority": 3,
    },

    "roa": {
        "name": "总资产报酬率 ROA",
        "group": "return_efficiency",
        "field_name": "roa",
        "metric_type": "percent",
        "unit": "%",
        "description": "总资产报酬率，用于观察全部资产创造收益的能力。",
        "higher_is_better": True,
        "priority": 4,
    },

    "npta": {
        "name": "总资产净利润率",
        "group": "return_efficiency",
        "field_name": "npta",
        "metric_type": "percent",
        "unit": "%",
        "description": "总资产净利润，用于观察资产转化为净利润的效率。",
        "higher_is_better": True,
        "priority": 5,
    },

    "roic": {
        "name": "投入资本回报率 ROIC",
        "group": "return_efficiency",
        "field_name": "roic",
        "metric_type": "percent",
        "unit": "%",
        "description": "投入资本回报率，用于观察公司对投入资本的回报能力。",
        "higher_is_better": True,
        "priority": 6,
    },

    # =========================================================
    # 5. 营运效率与周转率 turnover_efficiency
    # =========================================================
    "inv_turn": {
        "name": "存货周转率",
        "group": "turnover_efficiency",
        "field_name": "inv_turn",
        "metric_type": "times",
        "unit": "次",
        "description": "存货周转率，用于观察存货周转效率。",
        "higher_is_better": True,
        "priority": 1,
    },

    "ar_turn": {
        "name": "应收账款周转率",
        "group": "turnover_efficiency",
        "field_name": "ar_turn",
        "metric_type": "times",
        "unit": "次",
        "description": "应收账款周转率，用于观察应收账款回收效率。",
        "higher_is_better": True,
        "priority": 2,
    },

    "ca_turn": {
        "name": "流动资产周转率",
        "group": "turnover_efficiency",
        "field_name": "ca_turn",
        "metric_type": "times",
        "unit": "次",
        "description": "流动资产周转率，用于观察流动资产使用效率。",
        "higher_is_better": True,
        "priority": 3,
    },

    "fa_turn": {
        "name": "固定资产周转率",
        "group": "turnover_efficiency",
        "field_name": "fa_turn",
        "metric_type": "times",
        "unit": "次",
        "description": "固定资产周转率，用于观察固定资产利用效率。",
        "higher_is_better": True,
        "priority": 4,
    },

    "assets_turn": {
        "name": "总资产周转率",
        "group": "turnover_efficiency",
        "field_name": "assets_turn",
        "metric_type": "times",
        "unit": "次",
        "description": "总资产周转率，用于观察全部资产创造收入的效率。",
        "higher_is_better": True,
        "priority": 5,
    },

    # =========================================================
    # 6. 流动性与偿债能力 liquidity_solvency
    # =========================================================
    "current_ratio": {
        "name": "流动比率",
        "group": "liquidity_solvency",
        "field_name": "current_ratio",
        "metric_type": "ratio",
        "unit": "ratio",
        "description": "流动资产对流动负债的覆盖能力。",
        "higher_is_better": True,
        "priority": 1,
    },

    "quick_ratio": {
        "name": "速动比率",
        "group": "liquidity_solvency",
        "field_name": "quick_ratio",
        "metric_type": "ratio",
        "unit": "ratio",
        "description": "剔除存货后流动资产对流动负债的覆盖能力。",
        "higher_is_better": True,
        "priority": 2,
    },

    "cash_ratio": {
        "name": "现金比率",
        "group": "liquidity_solvency",
        "field_name": "cash_ratio",
        "metric_type": "ratio",
        "unit": "ratio",
        "description": "现金类资产对流动负债的覆盖能力。",
        "higher_is_better": True,
        "priority": 3,
    },

    "debt_to_assets": {
        "name": "资产负债率",
        "group": "liquidity_solvency",
        "field_name": "debt_to_assets",
        "metric_type": "percent",
        "unit": "%",
        "description": "负债合计相对资产总计的比例，用于观察整体财务杠杆。",
        "higher_is_better": False,
        "priority": 4,
    },

    "assets_to_eqt": {
        "name": "权益乘数",
        "group": "liquidity_solvency",
        "field_name": "assets_to_eqt",
        "metric_type": "ratio",
        "unit": "ratio",
        "description": "资产相对股东权益的倍数，用于观察财务杠杆水平。",
        "higher_is_better": False,
        "priority": 5,
    },

    # =========================================================
    # 7. 资本、债务与自由现金流 capital_cashflow_debt
    # =========================================================
    "ebit": {
        "name": "EBIT",
        "group": "capital_cashflow_debt",
        "field_name": "ebit",
        "metric_type": "amount",
        "unit": "amount",
        "description": "息税前利润，用于观察不考虑利息和所得税前的盈利能力。",
        "higher_is_better": True,
        "priority": 1,
    },

    "ebitda": {
        "name": "EBITDA",
        "group": "capital_cashflow_debt",
        "field_name": "ebitda",
        "metric_type": "amount",
        "unit": "amount",
        "description": "息税折旧摊销前利润，用于观察经营性现金盈利能力的近似口径。",
        "higher_is_better": True,
        "priority": 2,
    },

    "fcff": {
        "name": "FCFF",
        "group": "capital_cashflow_debt",
        "field_name": "fcff",
        "metric_type": "amount",
        "unit": "amount",
        "description": "企业自由现金流，用于观察企业整体自由现金创造能力。",
        "higher_is_better": True,
        "priority": 3,
    },

    "fcfe": {
        "name": "FCFE",
        "group": "capital_cashflow_debt",
        "field_name": "fcfe",
        "metric_type": "amount",
        "unit": "amount",
        "description": "股权自由现金流，用于观察归属于股东口径的自由现金创造能力。",
        "higher_is_better": True,
        "priority": 4,
    },

    "interestdebt": {
        "name": "带息债务",
        "group": "capital_cashflow_debt",
        "field_name": "interestdebt",
        "metric_type": "amount",
        "unit": "amount",
        "description": "公司需要承担利息成本的债务规模。",
        "higher_is_better": False,
        "priority": 5,
    },

    "netdebt": {
        "name": "净债务",
        "group": "capital_cashflow_debt",
        "field_name": "netdebt",
        "metric_type": "amount",
        "unit": "amount",
        "description": "扣除现金后的债务压力，用于观察净债务负担。",
        "higher_is_better": False,
        "priority": 6,
    },

    "working_capital": {
        "name": "营运资金",
        "group": "capital_cashflow_debt",
        "field_name": "working_capital",
        "metric_type": "amount",
        "unit": "amount",
        "description": "营运资金，用于观察短期经营资金余量。",
        "higher_is_better": None,
        "priority": 7,
    },

    "invest_capital": {
        "name": "全部投入资本",
        "group": "capital_cashflow_debt",
        "field_name": "invest_capital",
        "metric_type": "amount",
        "unit": "amount",
        "description": "全部投入资本，用于观察公司资本投入规模。",
        "higher_is_better": None,
        "priority": 8,
    },

    # =========================================================
    # 8. 基础利润质量与扣非指标 earnings_quality_basic
    # =========================================================
    "extra_item": {
        "name": "非经常性损益",
        "group": "earnings_quality_basic",
        "field_name": "extra_item",
        "metric_type": "amount",
        "unit": "amount",
        "description": "非经常性损益金额，用于观察利润是否受到一次性项目影响。",
        "higher_is_better": None,
        "priority": 1,
    },

    "profit_dedt": {
        "name": "扣非净利润",
        "group": "earnings_quality_basic",
        "field_name": "profit_dedt",
        "metric_type": "amount",
        "unit": "amount",
        "description": "扣除非经常性损益后的净利润，用于观察更可持续的盈利能力。",
        "higher_is_better": True,
        "priority": 2,
    },

    "op_income": {
        "name": "经营活动净收益",
        "group": "earnings_quality_basic",
        "field_name": "op_income",
        "metric_type": "amount",
        "unit": "amount",
        "description": "经营活动净收益，用于观察利润中经营活动贡献的基础收益。",
        "higher_is_better": True,
        "priority": 3,
    },
}


CROSS_STATEMENT_METRIC_REGISTRY = {
    # =========================================================
    # 1. 收入质量诊断 revenue_quality
    # =========================================================
    "sales_cash_to_revenue": {
        "name": "销售收现/营业收入",
        "group": "revenue_quality",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "cashflow.c_fr_sale_sg / income.revenue",
        "depends_on": [
            "cashflow.c_fr_sale_sg",
            "income.revenue",
        ],
        "description": "衡量营业收入是否有销售现金流入支撑。",
        "interpretation": (
            "比例越接近或高于 1，通常说明收入现金回款较好；"
            "若持续低于 1，需要结合应收账款、合同资产和收入增长判断收入质量。"
        ),
        "higher_is_better": True,
        "priority": 1,
    },

    "operating_receivables_to_revenue": {
        "name": "经营性应收/营业收入",
        "group": "revenue_quality",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "balance_sheet.operating_receivables / income.revenue",
        "depends_on": [
            "balance_sheet.effective_receivables",
            "balance_sheet.contract_assets",
            "income.revenue",
        ],
        "description": "衡量应收票据及应收账款、合同资产等经营性应收项目相对营业收入的占用程度。",
        "interpretation": (
            "比例越高，说明收入对应的回款和结算压力可能越大；"
            "若收入增长同时该比例上升，需要关注收入质量。"
        ),
        "higher_is_better": False,
        "priority": 2,
    },

    "receivable_inventory_to_revenue": {
        "name": "经营性应收与存货/营业收入",
        "group": "revenue_quality",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "(balance_sheet.operating_receivables + balance_sheet.inventories) / income.revenue",
        "depends_on": [
            "balance_sheet.effective_receivables",
            "balance_sheet.contract_assets",
            "balance_sheet.inventories",
            "income.revenue",
        ],
        "description": "衡量应收、合同资产和存货对收入的综合占用程度。",
        "interpretation": (
            "比例越高，说明收入增长可能伴随更多营运资产占用；"
            "需要结合经营现金流和存货周转判断是否存在回款或库存压力。"
        ),
        "higher_is_better": False,
        "priority": 3,
    },

    # =========================================================
    # 2. 利润质量诊断 profit_quality
    # =========================================================
    "ocf_to_net_income": {
        "name": "经营现金流/净利润",
        "group": "profit_quality",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "cashflow.n_cashflow_act / income.n_income",
        "depends_on": [
            "cashflow.n_cashflow_act",
            "income.n_income",
        ],
        "description": "衡量净利润是否有经营现金流支撑。",
        "interpretation": (
            "比例越高，通常利润现金含量越好；"
            "若长期低于 1，说明净利润转化为经营现金流的能力偏弱。"
        ),
        "higher_is_better": True,
        "priority": 1,
    },

    "profit_cash_gap": {
        "name": "经营现金流与净利润差额",
        "group": "profit_quality",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "cashflow.n_cashflow_act - income.n_income",
        "depends_on": [
            "cashflow.n_cashflow_act",
            "income.n_income",
        ],
        "description": "经营现金流净额与净利润之间的差额。",
        "interpretation": (
            "为正通常说明经营现金流覆盖净利润；"
            "为负说明净利润没有充分转化为经营现金流。"
        ),
        "higher_is_better": True,
        "priority": 2,
    },

    "deducted_profit_to_parent_net_income": {
        "name": "扣非净利润/归母净利润",
        "group": "profit_quality",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "fina_indicator.profit_dedt / income.n_income_attr_p",
        "depends_on": [
            "fina_indicator.profit_dedt",
            "income.n_income_attr_p",
        ],
        "description": "衡量归母净利润中有多少由扣非后利润支撑。",
        "interpretation": (
            "比例越高，通常利润可持续性越好；"
            "比例偏低时，需要关注非经常性损益对归母净利润的影响。"
        ),
        "higher_is_better": True,
        "priority": 3,
    },

    "impairment_to_parent_net_income": {
        "name": "减值损失/归母净利润",
        "group": "profit_quality",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "income.total_impairment_loss / income.n_income_attr_p",
        "depends_on": [
            "income.assets_impair_loss",
            "income.credit_impa_loss",
            "income.oth_impair_loss_assets",
            "income.n_income_attr_p",
        ],
        "description": "衡量各类减值损失相对归母净利润的影响程度。",
        "interpretation": (
            "比例越高，说明利润受资产或信用减值影响越明显；"
            "需要结合应收、存货、商誉、无形资产等资产质量判断。"
        ),
        "higher_is_better": False,
        "priority": 4,
    },

    # =========================================================
    # 3. 现金转化质量诊断 cash_conversion_quality
    # =========================================================
    "simple_free_cashflow": {
        "name": "简化自由现金流",
        "group": "cash_conversion_quality",
        "metric_type": "amount",
        "unit": "amount",
        "formula": "cashflow.n_cashflow_act - cashflow.c_pay_acq_const_fiolta",
        "depends_on": [
            "cashflow.n_cashflow_act",
            "cashflow.c_pay_acq_const_fiolta",
        ],
        "description": "经营现金流扣除购建长期资产支付现金后的简化自由现金流。",
        "interpretation": (
            "为正通常说明经营现金流覆盖资本开支后仍有剩余；"
            "为负则可能说明扩张或资本开支消耗了经营现金流。"
        ),
        "higher_is_better": True,
        "priority": 1,
    },

    "simple_fcf_to_net_income": {
        "name": "简化自由现金流/净利润",
        "group": "cash_conversion_quality",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "(cashflow.n_cashflow_act - cashflow.c_pay_acq_const_fiolta) / income.n_income",
        "depends_on": [
            "cashflow.n_cashflow_act",
            "cashflow.c_pay_acq_const_fiolta",
            "income.n_income",
        ],
        "description": "衡量净利润最终转化为扣除资本开支后的自由现金流能力。",
        "interpretation": (
            "比例越高，现金转化质量越好；"
            "若长期为负，需要关注资本开支压力或利润现金含量不足。"
        ),
        "higher_is_better": True,
        "priority": 2,
    },

    "ocf_to_operating_profit": {
        "name": "经营现金流/营业利润",
        "group": "cash_conversion_quality",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "cashflow.n_cashflow_act / income.operate_profit",
        "depends_on": [
            "cashflow.n_cashflow_act",
            "income.operate_profit",
        ],
        "description": "衡量营业利润是否能转化为经营现金流。",
        "interpretation": (
            "比例越高，经营利润现金含量越好；"
            "比例偏低时，需要关注应收、存货和营运资本占款。"
        ),
        "higher_is_better": True,
        "priority": 3,
    },

    # =========================================================
    # 4. 偿债压力诊断 debt_service_pressure
    # =========================================================
    "ocf_to_short_interest_debt": {
        "name": "经营现金流/短期有息负债",
        "group": "debt_service_pressure",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "cashflow.n_cashflow_act / balance_sheet.short_term_interest_debt",
        "depends_on": [
            "cashflow.n_cashflow_act",
            "balance_sheet.st_borr",
            "balance_sheet.non_cur_liab_due_1y",
            "balance_sheet.st_bonds_payable",
        ],
        "description": "衡量经营现金流对短期有息债务的覆盖能力。",
        "interpretation": (
            "比例越高，短期有息债务压力越可控；"
            "比例偏低时，需要关注再融资和现金储备。"
        ),
        "higher_is_better": True,
        "priority": 1,
    },

    "debt_repayment_to_ocf": {
        "name": "偿还债务现金支出/经营现金流",
        "group": "debt_service_pressure",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "cashflow.c_prepay_amt_borr / cashflow.n_cashflow_act",
        "depends_on": [
            "cashflow.c_prepay_amt_borr",
            "cashflow.n_cashflow_act",
        ],
        "description": "衡量偿还债务现金支出相对经营现金流的压力。",
        "interpretation": (
            "比例越高，说明经营现金流中较大部分需要用于偿债；"
            "若超过或接近 1，偿债压力较大。"
        ),
        "higher_is_better": False,
        "priority": 2,
    },

    "dividend_interest_to_ocf": {
        "name": "分红付息现金支出/经营现金流",
        "group": "debt_service_pressure",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "cashflow.c_pay_dist_dpcp_int_exp / cashflow.n_cashflow_act",
        "depends_on": [
            "cashflow.c_pay_dist_dpcp_int_exp",
            "cashflow.n_cashflow_act",
        ],
        "description": "衡量分红、利润分配和偿付利息支出对经营现金流的消耗。",
        "interpretation": (
            "比例越高，说明经营现金流被分红付息消耗越多；"
            "需要结合融资现金流和债务结构判断资金压力。"
        ),
        "higher_is_better": False,
        "priority": 3,
    },

    "netdebt_to_ocf": {
        "name": "净债务/经营现金流",
        "group": "debt_service_pressure",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "fina_indicator.netdebt / cashflow.n_cashflow_act",
        "depends_on": [
            "fina_indicator.netdebt",
            "cashflow.n_cashflow_act",
        ],
        "description": "衡量经营现金流覆盖净债务所需的年限近似值。",
        "interpretation": (
            "比例越高，说明净债务相对经营现金流越重；"
            "若为负，可能代表净现金状态。"
        ),
        "higher_is_better": False,
        "priority": 4,
    },

    # =========================================================
    # 5. 资本开支与扩张压力 capex_expansion_pressure
    # =========================================================
    "capex_to_ocf": {
        "name": "资本开支/经营现金流",
        "group": "capex_expansion_pressure",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "cashflow.c_pay_acq_const_fiolta / cashflow.n_cashflow_act",
        "depends_on": [
            "cashflow.c_pay_acq_const_fiolta",
            "cashflow.n_cashflow_act",
        ],
        "description": "衡量资本开支对经营现金流的消耗程度。",
        "interpretation": (
            "比例越高，说明经营现金流越多被资本开支消耗；"
            "如果长期高于 1，可能需要依赖外部融资支持扩张。"
        ),
        "higher_is_better": False,
        "priority": 1,
    },

    "capex_to_revenue": {
        "name": "资本开支/营业收入",
        "group": "capex_expansion_pressure",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "cashflow.c_pay_acq_const_fiolta / income.revenue",
        "depends_on": [
            "cashflow.c_pay_acq_const_fiolta",
            "income.revenue",
        ],
        "description": "衡量资本开支相对收入规模的强度。",
        "interpretation": (
            "比例越高，说明扩张投入或长期资产投入强度越大；"
            "需要结合行业属性和在建工程判断是否合理。"
        ),
        "higher_is_better": None,
        "priority": 2,
    },

    "capex_to_depreciation_amortization": {
        "name": "资本开支/折旧摊销",
        "group": "capex_expansion_pressure",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "cashflow.c_pay_acq_const_fiolta / (cashflow.depr_fa_coga_dpba + cashflow.amort_intang_assets)",
        "depends_on": [
            "cashflow.c_pay_acq_const_fiolta",
            "cashflow.depr_fa_coga_dpba",
            "cashflow.amort_intang_assets",
        ],
        "description": "衡量资本开支相对折旧摊销的倍数。",
        "interpretation": (
            "比例显著高于 1，通常说明公司处于扩张或较高资本投入阶段；"
            "接近或低于 1，可能说明更多是维持性资本开支。"
        ),
        "higher_is_better": None,
        "priority": 3,
    },

    # =========================================================
    # 6. 营运资本占款压力 working_capital_pressure
    # =========================================================
    "net_operating_working_capital_to_revenue": {
        "name": "净经营营运资本/营业收入",
        "group": "working_capital_pressure",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "balance_sheet.net_operating_working_capital / income.revenue",
        "depends_on": [
            "balance_sheet.effective_receivables",
            "balance_sheet.contract_assets",
            "balance_sheet.inventories",
            "balance_sheet.effective_payables",
            "balance_sheet.adv_receipts",
            "balance_sheet.contract_liab",
            "income.revenue",
        ],
        "description": "衡量经营环节净占用资金相对收入规模的程度。",
        "interpretation": (
            "比例越高，说明经营活动对营运资本占用越重；"
            "需要结合经营现金流和周转率判断资金效率。"
        ),
        "higher_is_better": False,
        "priority": 1,
    },

    "operating_receivables_to_sales_cash": {
        "name": "经营性应收/销售收现",
        "group": "working_capital_pressure",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "balance_sheet.operating_receivables / cashflow.c_fr_sale_sg",
        "depends_on": [
            "balance_sheet.effective_receivables",
            "balance_sheet.contract_assets",
            "cashflow.c_fr_sale_sg",
        ],
        "description": "衡量经营性应收相对销售收现的压力。",
        "interpretation": (
            "比例越高，说明应收和合同资产相对销售回款越重；"
            "需要关注回款周期和收入确认质量。"
        ),
        "higher_is_better": False,
        "priority": 2,
    },

    "working_capital_adjustment_to_ocf": {
        "name": "营运资本现金流调节/经营现金流",
        "group": "working_capital_pressure",
        "metric_type": "ratio",
        "unit": "ratio",
        "formula": "(cashflow.decr_inventories + cashflow.decr_oper_payable + cashflow.incr_oper_payable) / cashflow.n_cashflow_act",
        "depends_on": [
            "cashflow.decr_inventories",
            "cashflow.decr_oper_payable",
            "cashflow.incr_oper_payable",
            "cashflow.n_cashflow_act",
        ],
        "description": "衡量存货、经营性应收和经营性应付变化对经营现金流的相对影响。",
        "interpretation": (
            "比例较高时，说明经营现金流较大程度受到营运资本变化影响；"
            "需要判断现金流改善是否来自应付款增加或库存释放。"
        ),
        "higher_is_better": None,
        "priority": 3,
    },
}