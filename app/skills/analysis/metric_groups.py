# ============================================================
# 1. 暴露给大模型选择的 metric_groups
# ============================================================

INCOME_GROUPS = {
    "profit_scale_layers": {
        "name": "收入与利润层级",
        "description":
            """
            用于查看利润表从收入到营业利润、利润总额、净利润的核心金额层级。
            适合回答：公司收入规模和利润规模如何变化、营业利润和净利润是否同步变化、利润主要层级是否出现断层。
            不负责回答毛利率、净利率、ROE、ROA 等标准盈利能力比率，这些应由 fina_indicator tool 提供。
            """,
        "metrics": [
            "total_revenue_amount",
            "revenue_amount",
            "operating_profit_amount",
            "total_profit_amount",
            "net_income_amount",
        ],
    },

    "cost_expense_amounts": {
        "name": "成本与期间费用金额",
        "description":
            """
            用于拆解营业成本、营业总成本、销售费用、管理费用、税金及附加等利润表成本费用金额。
            适合回答：利润变化是否来自成本上升、销售费用或管理费用扩张、营业总成本是否明显增加。
            不负责输出销售费用率、管理费用率、期间费用率、成本率等标准费用率，这些应由 fina_indicator tool 提供。
            """,
        "metrics": [
            "operating_cost_amount",
            "total_cogs_amount",
            "selling_expense_amount",
            "admin_expense_amount",
            "tax_surcharge_amount",
        ],
    },

    "rd_and_finance_detail": {
        "name": "研发投入与财务费用拆解",
        "description":
            """
            用于查看研发费用、财务费用、利息费用、利息收入和净利息费用。
            适合回答：公司是否加大研发投入、财务费用变化是否由利息支出驱动、债务成本是否对利润形成压力。
            如果要判断债务压力，应结合 balance_sheet 的债务期限结构和 cashflow 的筹资/偿债现金流。
            """,
        "metrics": [
            "rd_expense_amount",
            "finance_expense_amount",
            "interest_expense_amount",
            "interest_income_amount",
            "net_interest_expense_amount",
        ],
    },

    "non_core_profit_sources": {
        "name": "非主营损益与一次性收益",
        "description":
            """
            用于分析投资收益、公允价值变动收益、其他收益、资产处置收益、营业外收支等非主营项目。
            适合回答：利润是否依赖投资收益、公允价值变动、政府补助或资产处置等非经营性因素。
            不直接等同于扣非净利润；扣非净利润和非经常性损益应优先由 fina_indicator tool 提供。
            """,
        "metrics": [
            "investment_income_amount",
            "fair_value_change_gain_amount",
            "other_income_amount",
            "asset_disposal_income_amount",
            "net_non_operating_income_amount",
            "non_core_profit_total_amount",
            "non_core_profit_to_total_profit",
        ],
    },

    "impairment_losses": {
        "name": "减值损失",
        "description":
            """
            用于查看资产减值损失、信用减值损失、其他资产减值损失及其合计影响。
            适合回答：利润是否受到减值拖累、应收类资产是否可能伴随信用减值压力、资产质量风险是否已经反映到利润表。
            如果要判断减值来源，应结合 balance_sheet 的应收、存货、商誉、无形资产、在建工程等资产结构证据。
            """,
        "metrics": [
            "asset_impairment_loss_amount",
            "credit_impairment_loss_amount",
            "other_asset_impairment_loss_amount",
            "total_impairment_loss_amount",
            "impairment_to_operating_profit",
        ],
    },

    "profit_attribution": {
        "name": "归母与少数股东损益",
        "description":
            """
            用于分析净利润在归母股东和少数股东之间的分配。
            适合回答：净利润增长是否真正归属于母公司股东、少数股东损益占比是否较高、归母净利润与整体净利润是否背离。
            不负责输出每股收益、扣非净利润等标准股东回报指标，这些应由 fina_indicator tool 提供。
            """,
        "metrics": [
            "parent_net_income_amount",
            "minority_gain_amount",
            "parent_net_income_share",
            "minority_gain_share",
        ],
    },

    "comprehensive_income": {
        "name": "其他综合收益与综合收益",
        "description":
            """
            用于分析其他综合收益、归母综合收益与归母净利润之间的差异。
            适合回答：是否存在未计入当期损益但影响股东权益的收益或损失、综合收益是否明显偏离净利润。
            该 group 适合在利润表质量分析或权益变化解释时调用。
            """,
        "metrics": [
            "other_comprehensive_income_amount",
            "parent_comprehensive_income_amount",
            "comprehensive_income_gap_amount",
            "comprehensive_income_gap_to_parent_net_income",
        ],
    },
}

BALANCE_SHEET_GROUPS = {
    "asset_scale_structure": {
        "name": "资产规模与资产结构",
        "description":
            """
            用于分析公司资产端的结构特征，包括流动资产、非流动资产、固定资产、货币资金在总资产中的占比。
            适合回答：公司是轻资产还是重资产、资产结构是否发生明显变化、现金资产占比是否偏高或偏低。
            不直接回答偿债能力强弱，偿债能力应结合 fina_indicator 的流动比率、速动比率、资产负债率等指标。
            """,
        "metrics": [
            "current_asset_ratio",
            "noncurrent_asset_ratio",
            "fixed_asset_ratio",
            "cash_asset_ratio",
        ],
    },

    "debt_maturity_structure": {
        "name": "债务期限结构与短债压力",
        "description":
            """
            用于拆解有息负债的期限结构，重点观察短期有息负债、长期有息负债、短债占有息负债比例、现金对短债的覆盖。
            适合回答：公司短期债务压力是否较大、债务期限是否偏短、账面现金能否覆盖短期有息债务。
            该 group 不负责输出资产负债率、净债务、有息负债总额等通用指标，这些应优先由 fina_indicator tool 提供。
            """,
        "metrics": [
            "short_term_interest_debt",
            "long_term_interest_debt",
            "debt_maturity_pressure",
            "cash_to_short_debt",
        ],
    },

    "receivables_inventory": {
        "name": "应收、存货与经营占款",
        "description":
            """
            用于分析经营性资产占用，重点观察应收票据及应收账款、合同资产、存货对总资产的占用。
            适合回答：收入增长是否伴随应收和存货明显增加、资产是否被客户回款和库存占用、是否存在收入质量或库存压力线索。
            该 group 只提供资产负债表侧的占款证据；判断收入质量时，应结合 income 的收入增速和 cashflow 的销售收现、经营现金流。
            """,
        "metrics": [
            "operating_receivables",
            "receivable_asset_ratio",
            "inventory_asset_ratio",
            "receivable_inventory_ratio",
            "contract_asset_ratio",
        ],
    },

    "payables_contract_liability": {
        "name": "应付、预收与合同负债",
        "description":
            """
            用于分析经营性负债和上下游占款能力，重点观察应付票据及应付账款、预收款项、合同负债等经营性资金来源。
            适合回答：公司是否能占用供应商或客户资金、合同负债是否提供经营资金支持、经营环节是占用资金还是释放资金。
            该 group 适合与 receivables_inventory 联合使用，用于分析净经营营运资本和上下游议价能力。
            """,
        "metrics": [
            "operating_payables",
            "payable_liability_ratio",
            "advance_contract_liab_ratio",
            "net_operating_working_capital",
        ],
    },

    "soft_asset_risk": {
        "name": "商誉与无形资产风险",
        "description":
            """
            用于分析偏软性资产占比，重点观察商誉、无形资产以及二者合计占总资产的比例。
            适合回答：公司是否存在商誉减值风险、无形资产占比是否偏高、资产质量是否依赖较多非实物资产。
            该 group 不直接判断利润质量，若需要判断减值风险对利润的影响，应结合 income 的资产减值损失、净利润变化。
            """,
        "metrics": [
            "goodwill_asset_ratio",
            "intangible_asset_ratio",
            "goodwill_intangible_ratio",
        ],
    },

    "construction_asset_risk": {
        "name": "在建工程与扩产风险",
        "description":
            """用于分析在建工程和扩产相关风险，重点观察在建工程占总资产比例、在建工程相对固定资产的比例。
            适合回答：公司是否处于扩产周期、在建项目规模是否偏大、未来是否存在转固、折旧、产能消化或资本开支压力。
            该 group 适合与 cashflow 的投资现金流、购建固定资产现金支出等指标联合使用。
            """,
        "metrics": [
            "cip_asset_ratio",
            "cip_fixed_asset_ratio",
        ],
    },
}

"""
CashFlow metric groups and registry.

设计原则：
1. CashFlow tool 不重复 FinaIndicator / CrossStatement 中已有的成熟指标。
2. CashFlow tool 重点解释现金流形成过程，而不是直接给最终财务结论。
3. Agent 选择 group，不直接选择大量 metric_code。
4. 每个 group 语义明确，便于 ReAct Agent 精准调用。
5. Tool 最终输出仍然只建议输出 name、unit、value。
"""
CASHFLOW_GROUPS = {
    "operating_cash_inflows": {
        "name": "经营现金流入结构",
        "description":
            """
            用于分析经营活动现金流入是否主要来自销售回款，以及其他经营现金流入占比是否异常。
            适合回答：销售收现是否支撑经营现金流、经营现金流入来源是否健康。
            判断收入质量时，应结合 income 的收入规模和 balance_sheet 的应收、合同资产变化。
            """,
        "metrics": [
            "sales_cash_received",
            "operating_cash_inflow_total",
            "sales_cash_inflow_share",
            "other_operating_inflow_share",
        ],
    },

    "operating_cash_outflows": {
        "name": "经营现金流出结构",
        "description":
            """
            用于分析经营活动现金流出主要流向采购、人工、税费等项目。
            适合回答：经营现金流出压力来自采购付款、人工支出还是税费支出。
            成本率、费用率仍应由 fina_indicator 或 income tool 提供。
            """,
        "metrics": [
            "goods_services_cash_paid",
            "employee_cash_paid",
            "taxes_cash_paid",
            "operating_cash_outflow_total",
            "purchase_cash_outflow_share",
        ],
    },

    "operating_cash_net": {
        "name": "经营现金流净额",
        "description":
            """
            用于观察经营活动最终沉淀下来的净现金流，以及经营现金流入转化为净额的能力。
            适合回答：经营活动是否真正产生现金、经营现金流净额是否偏弱。
            OCF/净利润等跨表指标应由 cross_statement tool 处理。
            """,
        "metrics": [
            "operating_net_cashflow",
            "operating_cashflow_inflow_margin",
        ],
    },

    "investing_capex_structure": {
        "name": "投资现金流与资本开支",
        "description":
            """
            用于分析投资活动现金流和资本开支压力，重点观察购建长期资产支付的现金。
            适合回答：公司是否处于扩产周期、投资净流出是否主要由资本开支驱动。
            扩产风险应结合 balance_sheet 的在建工程和固定资产结构。
            """,
        "metrics": [
            "investment_cash_inflow_total",
            "capex_cash_paid",
            "investment_cash_paid",
            "investment_cash_outflow_total",
            "investing_net_cashflow",
            "capex_outflow_share",
        ],
    },

    "financing_cashflow_structure": {
        "name": "筹资现金流结构",
        "description":
            """
            用于分析公司融资和偿债动作，包括股权融资、债务融资、偿债、分红付息和筹资现金流净额。
            适合回答：公司是否依赖外部融资、融资主要来自债务还是股权、是否存在偿债或分红付息压力。
            债务压力应结合 balance_sheet 的债务期限结构和 fina_indicator 的杠杆指标。
            """,
        "metrics": [
            "equity_financing_cash_received",
            "debt_financing_cash_received",
            "financing_cash_inflow_total",
            "debt_repayment_cash_paid",
            "dividend_interest_cash_paid",
            "financing_cash_outflow_total",
            "financing_net_cashflow",
        ],
    },

    "cash_balance_change": {
        "name": "现金及现金等价物变化",
        "description":
            """
            用于分析现金及现金等价物期初、期末和本期净增加额。
            适合回答：公司账面现金是否增加、现金变化方向是否与三大现金流净额一致。
            现金偿债能力应结合 balance_sheet 的短债结构和 fina_indicator 的现金比率。
            """,
        "metrics": [
            "beginning_cash_equivalent",
            "ending_cash_equivalent",
            "net_cash_equivalent_increase",
        ],
    },

    "indirect_operating_reconciliation": {
        "name": "经营现金流间接法调节",
        "description":
            """
            用于解释净利润如何调节为经营现金流，重点看折旧摊销、存货变化、经营性应收变化和经营性应付变化。
            适合回答：净利润为什么没有变成现金、经营现金流改善是否来自营运资本变化。
            该 group 适合和 income 的净利润、balance_sheet 的应收存货占款一起使用。
            """,
        "metrics": [
            "indirect_net_profit_base",
            "depreciation_amortization_amount",
            "inventory_decrease_cash_effect",
            "operating_receivable_decrease_cash_effect",
            "operating_payable_increase_cash_effect",
            "indirect_operating_cashflow",
        ],
    },
}


"""
FinaIndicator metric groups and registry.

设计原则：
1. FinaIndicator 是 TuShare 已计算好的标准指标表。
2. Tool 不再手动计算复杂指标，只按 field_name 从 ORM 直接读取。
3. REGISTRY 只注册当前 ORM 中最有价值的 45 个指标。
4. 不把 FinaIndicator 做成“全量指标仓库”，而是做成“标准指标摘要层”。
5. Tool 最终输出建议只输出 name、unit、value。
"""
FINA_INDICATOR_GROUPS = {
    "per_share_value": {
        "name": "每股与股东价值指标",
        "description":
            """
            用于查看每股收益、每股净资产、每股现金流和每股自由现金流等股东价值相关指标。
            适合回答：每股盈利能力、每股资产价值、每股现金创造能力是否改善。
            不负责解释利润或现金流形成过程；形成过程应结合 income 和 cashflow tool。
            """,
        "metrics": [
            "eps",
            "dt_eps",
            "bps",
            "ocfps",
            "cfps",
            "fcff_ps",
            "fcfe_ps",
        ],
    },

    "profitability_margin": {
        "name": "盈利能力与利润率",
        "description":
            """
            用于查看公司销售毛利率、销售净利率、净利润率、营业利润率和 EBIT 利润率等标准盈利能力指标。
            适合回答：公司盈利能力强不强、利润率是否改善、经营利润率是否承压。
            不负责拆解具体收入、成本、费用金额；金额形成过程应由 income tool 提供。
            """,
        "metrics": [
            "grossprofit_margin",
            "netprofit_margin",
            "profit_to_gr",
            "op_of_gr",
            "ebit_of_gr",
        ],
    },

    "expense_cost_margin": {
        "name": "成本费用率",
        "description":
            """
            用于查看销售成本率、期间费用率、销售费用率、管理费用率、财务费用率和资产减值损失占收入比例。
            适合回答：利润率变化是否受到成本率或费用率拖累、费用控制是否改善。
            不负责输出具体费用金额；销售费用、管理费用、财务费用金额应由 income tool 提供。
            """,
        "metrics": [
            "cogs_of_sales",
            "expense_of_sales",
            "saleexp_to_gr",
            "adminexp_of_gr",
            "finaexp_of_gr",
            "impai_ttm",
        ],
    },

    "return_efficiency": {
        "name": "资产与资本回报率",
        "description":
            """
            用于查看 ROE、扣非 ROE、ROA、总资产净利率和 ROIC 等回报效率指标。
            适合回答：股东回报、资产回报、投入资本回报是否优秀或恶化。
            若要解释 ROE 变化原因，应结合 profitability_margin、turnover_efficiency 和 liquidity_solvency 分组。
            """,
        "metrics": [
            "roe",
            "roe_waa",
            "roe_dt",
            "roa",
            "npta",
            "roic",
        ],
    },

    "turnover_efficiency": {
        "name": "营运效率与周转率",
        "description":
            """
            用于查看存货、应收账款、流动资产、固定资产和总资产周转率。
            适合回答：公司资产使用效率、存货周转、应收账款回收效率是否改善。
            若要解释周转率变化，应结合 balance_sheet 的应收、存货和资产结构证据。
            """,
        "metrics": [
            "inv_turn",
            "ar_turn",
            "ca_turn",
            "fa_turn",
            "assets_turn",
        ],
    },

    "liquidity_solvency": {
        "name": "流动性与偿债能力",
        "description":
            """
            用于查看流动比率、速动比率、现金比率、资产负债率和权益乘数等标准偿债能力指标。
            适合回答：公司短期偿债能力、财务杠杆和总体债务压力如何。
            若要解释债务压力来源，应结合 balance_sheet 的债务期限结构和 cashflow 的筹资/偿债现金流。
            """,
        "metrics": [
            "current_ratio",
            "quick_ratio",
            "cash_ratio",
            "debt_to_assets",
            "assets_to_eqt",
        ],
    },

    "capital_cashflow_debt": {
        "name": "资本、债务与自由现金流",
        "description":
            """
            用于查看 EBIT、EBITDA、FCFF、FCFE、带息债务、净债务、营运资金和全部投入资本等指标。
            适合回答：公司经营现金创造能力、自由现金流、债务规模和资本投入规模如何。
            不负责解释现金流具体来源去向；现金流结构应由 cashflow tool 提供。
            """,
        "metrics": [
            "ebit",
            "ebitda",
            "fcff",
            "fcfe",
            "interestdebt",
            "netdebt",
            "working_capital",
            "invest_capital",
        ],
    },

    "earnings_quality_basic": {
        "name": "基础利润质量与扣非指标",
        "description":
            """
            用于查看非经常性损益、扣非净利润和经营活动净收益等基础利润质量指标。
            适合回答：净利润是否受到非经常性项目影响、扣非后盈利是否仍然稳定、经营性收益基础是否扎实。
            如果要详细拆解非主营损益来源，应结合 income 的非主营损益与一次性收益 group。
            """,
        "metrics": [
            "extra_item",
            "profit_dedt",
            "op_income",
        ],
    },
}


"""
Cross-statement metric groups and registry.

设计原则：
1. Cross tool 不补数据，不查数据库，只基于 Data 阶段已准备好的四类 records 计算。
2. Cross tool 不重复单表 tool 的明细输出，而是做跨表诊断。
3. 第一版只保留 6 个 group、20 个核心跨表指标。
4. Tool 最终输出仍然只建议输出 name、unit、value。
"""
CROSS_STATEMENT_GROUPS = {
    "revenue_quality": {
        "name": "收入质量诊断",
        "description":
            """
            用于判断收入是否有现金回款和资产负债表质量支撑。
            重点比较营业收入、销售收现、经营性应收、存货和合同资产。
            适合回答：收入增长是否扎实、是否存在收入确认快于现金回款、应收和存货是否占用过多资产。
            如果需要查看收入和利润金额明细，应结合 income tool；如果需要查看应收存货结构，应结合 balance_sheet tool。
            """,
        "metrics": [
            "sales_cash_to_revenue",
            "operating_receivables_to_revenue",
            "receivable_inventory_to_revenue",
        ],
    },

    "profit_quality": {
        "name": "利润质量诊断",
        "description":
            """
            用于判断利润是否有经营现金流和扣非利润支撑。
            重点比较净利润、归母净利润、经营现金流、扣非净利润和减值损失。
            适合回答：净利润是否可靠、是否有现金流支撑、是否受到非经常性损益或减值影响。
            如果需要拆解非主营损益来源，应结合 income tool；如果需要标准盈利指标，应结合 fina_indicator tool。
            """,
        "metrics": [
            "ocf_to_net_income",
            "profit_cash_gap",
            "deducted_profit_to_parent_net_income",
            "impairment_to_parent_net_income",
        ],
    },

    "cash_conversion_quality": {
        "name": "现金转化质量诊断",
        "description":
            """
            用于判断公司利润和经营活动最终能否转化为自由现金流。
            重点比较经营现金流、净利润、营业利润和资本开支。
            适合回答：公司赚钱是否真正产生现金、自由现金流是否充足、经营现金流是否被资本开支消耗。
            该 group 不解释现金流具体来源去向，现金流结构应结合 cashflow tool。
            """,
        "metrics": [
            "simple_free_cashflow",
            "simple_fcf_to_net_income",
            "ocf_to_operating_profit",
        ],
    },

    "debt_service_pressure": {
        "name": "偿债压力诊断",
        "description":
            """
            用于判断公司经营现金流和现金资源对债务压力的覆盖情况。
            重点比较经营现金流、短期有息负债、净债务、偿债现金支出和分红付息现金支出。
            适合回答：公司短期偿债压力是否大、是否依赖再融资、经营现金流能否支撑债务偿付。
            如果需要查看债务期限结构，应结合 balance_sheet tool；如果需要标准杠杆指标，应结合 fina_indicator tool。
            """,
        "metrics": [
            "ocf_to_short_interest_debt",
            "debt_repayment_to_ocf",
            "dividend_interest_to_ocf",
            "netdebt_to_ocf",
        ],
    },

    "capex_expansion_pressure": {
        "name": "资本开支与扩张压力诊断",
        "description":
            """
            用于判断资本开支是否对现金流造成压力，以及公司是否处于扩张周期。
            重点比较资本开支、经营现金流、营业收入和折旧摊销。
            适合回答：公司是否扩产、资本开支是否过重、经营现金流是否足以覆盖扩张投入。
            如果需要查看在建工程和固定资产结构，应结合 balance_sheet tool。
            """,
        "metrics": [
            "capex_to_ocf",
            "capex_to_revenue",
            "capex_to_depreciation_amortization",
        ],
    },

    "working_capital_pressure": {
        "name": "营运资本占款压力诊断",
        "description":
            """
            用于判断经营环节是否占用现金，以及应收、存货、应付变化对现金流的影响。
            重点比较净经营营运资本、收入、销售收现和现金流量表间接法中的营运资本调节项。
            适合回答：经营现金流变差是否由应收存货占用导致、现金流改善是否依赖应付款增加。
            该 group 适合与 balance_sheet 的应收存货占款和 cashflow 的间接法调节一起使用。
            """,
        "metrics": [
            "net_operating_working_capital_to_revenue",
            "operating_receivables_to_sales_cash",
            "working_capital_adjustment_to_ocf",
        ],
    },
}

