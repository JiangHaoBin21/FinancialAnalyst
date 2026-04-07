"""数据库 ORM 模型定义（与 scripts/init_db.py 对齐）"""

from sqlalchemy.orm import declarative_base
from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Boolean,
    Date,
    TIMESTAMP,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB


Base = declarative_base()


# =========================
# 1. 公司维表
# =========================
class Company(Base):
    __tablename__ = "dim_company"

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    ts_code = Column(String(20), unique=True, nullable=False, comment="Tushare 股票代码")
    symbol = Column(String(10), comment="股票短代码")
    name = Column(String(100), nullable=False, comment="公司名称")
    area = Column(String(50), comment="所属地区")
    industry = Column(String(100), comment="所属行业")
    market = Column(String(50), comment="市场类型（主板/创业板/科创板等）")
    exchange = Column(String(20), comment="交易所")
    list_date = Column(Date, comment="上市日期")

    is_active = Column(Boolean, nullable=False, default=True, comment="是否有效")
    source = Column(String(50), nullable=False, default="tushare", comment="数据来源")

    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )


# =========================
# 2. 利润表
# =========================
class Income(Base):
    __tablename__ = "fact_income"
    __table_args__ = (
        UniqueConstraint("ts_code", "end_date", "report_type", name="uq_fact_income"),
    )

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    ts_code = Column(String(20), nullable=False, comment="股票代码")

    ann_date = Column(Date, comment="公告日期")
    f_ann_date = Column(Date, comment="实际公告日期")
    end_date = Column(Date, nullable=False, comment="报告期")
    report_type = Column(String(20), comment="报表类型")
    comp_type = Column(String(20), comment="公司类型")

    basic_eps = Column(Numeric(20, 4), comment="基本每股收益")
    diluted_eps = Column(Numeric(20, 4), comment="稀释每股收益")
    total_revenue = Column(Numeric(20, 4), comment="营业总收入")
    revenue = Column(Numeric(20, 4), comment="营业收入")
    total_cogs = Column(Numeric(20, 4), comment="营业总成本")
    oper_cost = Column(Numeric(20, 4), comment="营业成本")
    sell_exp = Column(Numeric(20, 4), comment="销售费用")
    admin_exp = Column(Numeric(20, 4), comment="管理费用")
    fin_exp = Column(Numeric(20, 4), comment="财务费用")
    assets_impair_loss = Column(Numeric(20, 4), comment="资产减值损失")
    invest_income = Column(Numeric(20, 4), comment="投资收益")
    operate_profit = Column(Numeric(20, 4), comment="营业利润")
    total_profit = Column(Numeric(20, 4), comment="利润总额")
    income_tax = Column(Numeric(20, 4), comment="所得税费用")
    net_profit = Column(Numeric(20, 4), comment="净利润")
    n_income_attr_p = Column(Numeric(20, 4), comment="归属于母公司股东的净利润")
    minority_gain = Column(Numeric(20, 4), comment="少数股东损益")
    oth_compr_income = Column(Numeric(20, 4), comment="其他综合收益")
    compr_inc_attr_p = Column(Numeric(20, 4), comment="归属于母公司股东的综合收益总额")

    update_flag = Column(String(10), comment="更新标志")
    source = Column(String(50), nullable=False, default="tushare", comment="数据来源")

    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )


# =========================
# 3. 资产负债表
# =========================
class BalanceSheet(Base):
    __tablename__ = "fact_balance_sheet"
    __table_args__ = (
        UniqueConstraint("ts_code", "end_date", "report_type", name="uq_fact_balance_sheet"),
    )

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    ts_code = Column(String(20), nullable=False, comment="股票代码")

    ann_date = Column(Date, comment="公告日期")
    f_ann_date = Column(Date, comment="实际公告日期")
    end_date = Column(Date, nullable=False, comment="报告期")
    report_type = Column(String(20), comment="报表类型")
    comp_type = Column(String(20), comment="公司类型")

    total_share = Column(Numeric(20, 4), comment="期末总股本")
    money_cap = Column(Numeric(20, 4), comment="货币资金")
    trad_asset = Column(Numeric(20, 4), comment="交易性金融资产")
    notes_receiv = Column(Numeric(20, 4), comment="应收票据")
    accounts_receiv = Column(Numeric(20, 4), comment="应收账款")
    oth_receiv = Column(Numeric(20, 4), comment="其他应收款")
    prepayment = Column(Numeric(20, 4), comment="预付款项")
    inventories = Column(Numeric(20, 4), comment="存货")
    total_cur_assets = Column(Numeric(20, 4), comment="流动资产合计")
    fix_assets = Column(Numeric(20, 4), comment="固定资产")
    total_nca = Column(Numeric(20, 4), comment="非流动资产合计")
    total_assets = Column(Numeric(20, 4), comment="资产总计")

    short_term_borr = Column(Numeric(20, 4), comment="短期借款")
    notes_payable = Column(Numeric(20, 4), comment="应付票据")
    acct_payable = Column(Numeric(20, 4), comment="应付账款")
    adv_receipts = Column(Numeric(20, 4), comment="预收款项")
    total_cur_liab = Column(Numeric(20, 4), comment="流动负债合计")
    bond_payable = Column(Numeric(20, 4), comment="应付债券")
    total_ncl = Column(Numeric(20, 4), comment="非流动负债合计")
    total_liab = Column(Numeric(20, 4), comment="负债合计")

    total_hldr_eqy_exc_min_int = Column(Numeric(20, 4), comment="归属于母公司股东权益合计")
    total_hldr_eqy_inc_min_int = Column(Numeric(20, 4), comment="股东权益合计(含少数股东权益)")

    update_flag = Column(String(10), comment="更新标志")
    source = Column(String(50), nullable=False, default="tushare", comment="数据来源")

    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )


# =========================
# 4. 现金流量表
# =========================
class CashFlow(Base):
    __tablename__ = "fact_cashflow"
    __table_args__ = (
        UniqueConstraint("ts_code", "end_date", "report_type", name="uq_fact_cashflow"),
    )

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    ts_code = Column(String(20), nullable=False, comment="股票代码")

    ann_date = Column(Date, comment="公告日期")
    f_ann_date = Column(Date, comment="实际公告日期")
    end_date = Column(Date, nullable=False, comment="报告期")
    report_type = Column(String(20), comment="报表类型")
    comp_type = Column(String(20), comment="公司类型")

    c_fr_sale_sg = Column(Numeric(20, 4), comment="销售商品、提供劳务收到的现金")
    recp_tax_rends = Column(Numeric(20, 4), comment="收到的税费返还")
    n_depos_incr_fi = Column(Numeric(20, 4), comment="客户存款和同业存放款项净增加额")
    c_paid_goods_s = Column(Numeric(20, 4), comment="购买商品、接受劳务支付的现金")
    c_paid_to_for_empl = Column(Numeric(20, 4), comment="支付给职工以及为职工支付的现金")
    c_paid_for_taxes = Column(Numeric(20, 4), comment="支付的各项税费")
    n_cashflow_act = Column(Numeric(20, 4), comment="经营活动产生的现金流量净额")

    c_disp_withdrwl_invest = Column(Numeric(20, 4), comment="收回投资收到的现金")
    c_recp_return_invest = Column(Numeric(20, 4), comment="取得投资收益收到的现金")
    n_cashflow_inv_act = Column(Numeric(20, 4), comment="投资活动产生的现金流量净额")

    c_recp_borrow = Column(Numeric(20, 4), comment="取得借款收到的现金")
    proc_issue_bonds = Column(Numeric(20, 4), comment="发行债券收到的现金")
    c_prepay_amt_borr = Column(Numeric(20, 4), comment="偿还债务支付的现金")
    c_pay_dist_dpcp_int_exp = Column(Numeric(20, 4), comment="分配股利、利润或偿付利息支付的现金")
    n_cash_flows_fnc_act = Column(Numeric(20, 4), comment="筹资活动产生的现金流量净额")

    n_incr_cash_cash_equ = Column(Numeric(20, 4), comment="现金及现金等价物净增加额")
    c_cash_equ_beg_period = Column(Numeric(20, 4), comment="期初现金及现金等价物余额")
    c_cash_equ_end_period = Column(Numeric(20, 4), comment="期末现金及现金等价物余额")

    update_flag = Column(String(10), comment="更新标志")
    source = Column(String(50), nullable=False, default="tushare", comment="数据来源")

    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )


# =========================
# 5. 财务指标表
# =========================
class FinaIndicator(Base):
    __tablename__ = "fact_fina_indicator"
    __table_args__ = (
        UniqueConstraint("ts_code", "end_date", name="uq_fact_fina_indicator"),
    )

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    ts_code = Column(String(20), nullable=False, comment="股票代码")
    ann_date = Column(Date, comment="公告日期")
    end_date = Column(Date, nullable=False, comment="报告期")

    eps = Column(Numeric(20, 4), comment="每股收益")
    dt_eps = Column(Numeric(20, 4), comment="稀释每股收益/扣非每股收益（以 TuShare 字段定义为准）")
    total_revenue_ps = Column(Numeric(20, 4), comment="每股营业总收入")
    revenue_ps = Column(Numeric(20, 4), comment="每股营业收入")
    capital_rese_ps = Column(Numeric(20, 4), comment="每股资本公积")
    surplus_rese_ps = Column(Numeric(20, 4), comment="每股盈余公积")
    undist_profit_ps = Column(Numeric(20, 4), comment="每股未分配利润")

    extra_item = Column(Numeric(20, 4), comment="非经常性损益")
    profit_dedt = Column(Numeric(20, 4), comment="扣除非经常性损益后的净利润")
    gross_margin = Column(Numeric(20, 4), comment="毛利率")
    current_ratio = Column(Numeric(20, 4), comment="流动比率")
    quick_ratio = Column(Numeric(20, 4), comment="速动比率")
    cash_ratio = Column(Numeric(20, 4), comment="保守速动比率/现金比率")
    invturn_days = Column(Numeric(20, 4), comment="存货周转天数")
    arturn_days = Column(Numeric(20, 4), comment="应收账款周转天数")
    inv_turn = Column(Numeric(20, 4), comment="存货周转率")
    ar_turn = Column(Numeric(20, 4), comment="应收账款周转率")
    ca_turn = Column(Numeric(20, 4), comment="流动资产周转率")
    fa_turn = Column(Numeric(20, 4), comment="固定资产周转率")
    assets_turn = Column(Numeric(20, 4), comment="总资产周转率")

    op_income = Column(Numeric(20, 4), comment="经营活动净收益")
    valuechange_income = Column(Numeric(20, 4), comment="价值变动净收益")
    interst_income = Column(Numeric(20, 4), comment="利息费用")
    daa = Column(Numeric(20, 4), comment="折旧与摊销")
    ebit = Column(Numeric(20, 4), comment="息税前利润 EBIT")
    ebitda = Column(Numeric(20, 4), comment="息税折旧摊销前利润 EBITDA")
    fcff = Column(Numeric(20, 4), comment="企业自由现金流 FCFF")
    fcfe = Column(Numeric(20, 4), comment="股权自由现金流 FCFE")

    current_exint = Column(Numeric(20, 4), comment="无息流动负债")
    noncurrent_exint = Column(Numeric(20, 4), comment="无息非流动负债")
    interestdebt = Column(Numeric(20, 4), comment="带息债务")
    netdebt = Column(Numeric(20, 4), comment="净债务")
    tangible_asset = Column(Numeric(20, 4), comment="有形资产")
    working_capital = Column(Numeric(20, 4), comment="营运资金")
    networking_capital = Column(Numeric(20, 4), comment="营运流动资本")
    invest_capital = Column(Numeric(20, 4), comment="全部投入资本")
    retained_earnings = Column(Numeric(20, 4), comment="留存收益")

    diluted2_eps = Column(Numeric(20, 4), comment="期末摊薄每股收益")
    bps = Column(Numeric(20, 4), comment="每股净资产")
    ocfps = Column(Numeric(20, 4), comment="每股经营活动现金流量净额")
    retainedps = Column(Numeric(20, 4), comment="每股留存收益")
    cfps = Column(Numeric(20, 4), comment="每股现金流量净额")
    ebit_ps = Column(Numeric(20, 4), comment="每股 EBIT")
    fcff_ps = Column(Numeric(20, 4), comment="每股 FCFF")
    fcfe_ps = Column(Numeric(20, 4), comment="每股 FCFE")

    netprofit_margin = Column(Numeric(20, 4), comment="销售净利率")
    grossprofit_margin = Column(Numeric(20, 4), comment="销售毛利率")
    cogs_of_sales = Column(Numeric(20, 4), comment="销售成本率")
    expense_of_sales = Column(Numeric(20, 4), comment="销售期间费用率")
    profit_to_gr = Column(Numeric(20, 4), comment="净利润/营业总收入")
    saleexp_to_gr = Column(Numeric(20, 4), comment="销售费用/营业总收入")
    adminexp_of_gr = Column(Numeric(20, 4), comment="管理费用/营业总收入")
    finaexp_of_gr = Column(Numeric(20, 4), comment="财务费用/营业总收入")
    impai_ttm = Column(Numeric(20, 4), comment="资产减值损失/营业总收入")
    gc_of_gr = Column(Numeric(20, 4), comment="营业总成本/营业总收入")
    op_of_gr = Column(Numeric(20, 4), comment="营业利润/营业总收入")
    ebit_of_gr = Column(Numeric(20, 4), comment="EBIT/营业总收入")

    roe = Column(Numeric(20, 4), comment="净资产收益率 ROE")
    roe_waa = Column(Numeric(20, 4), comment="加权平均净资产收益率")
    roe_dt = Column(Numeric(20, 4), comment="扣非后 ROE")
    roa = Column(Numeric(20, 4), comment="总资产报酬率 ROA")
    npta = Column(Numeric(20, 4), comment="总资产净利润")
    roic = Column(Numeric(20, 4), comment="投入资本回报率 ROIC")
    roe_yearly = Column(Numeric(20, 4), comment="年化 ROE")
    roa2_yearly = Column(Numeric(20, 4), comment="年化 ROA")

    debt_to_assets = Column(Numeric(20, 4), comment="资产负债率")
    assets_to_eqt = Column(Numeric(20, 4), comment="权益乘数")
    dp_assets_to_eqt = Column(Numeric(20, 4), comment="权益乘数(杜邦分析口径)")

    update_flag = Column(String(10), comment="更新标志")
    source = Column(String(50), nullable=False, default="tushare", comment="数据来源")

    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )


# =========================
# 6. 派生指标表（核心）
# =========================
class DerivedMetrics(Base):
    __tablename__ = "fact_derived_metrics"
    __table_args__ = (
        UniqueConstraint("ts_code", "end_date", "metric_version", name="uq_fact_derived_metrics"),
    )

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    ts_code = Column(String(20), nullable=False, comment="股票代码")
    end_date = Column(Date, nullable=False, comment="报告期")

    revenue_yoy = Column(Numeric(20, 4), comment="营业收入同比增长率")
    revenue_cagr_3y = Column(Numeric(20, 4), comment="近三年营业收入复合增长率")
    net_profit_yoy = Column(Numeric(20, 4), comment="净利润同比增长率")
    net_profit_cagr_3y = Column(Numeric(20, 4), comment="近三年净利润复合增长率")

    gross_margin = Column(Numeric(20, 4), comment="毛利率")
    net_margin = Column(Numeric(20, 4), comment="净利率")
    roe = Column(Numeric(20, 4), comment="净资产收益率 ROE")
    roa = Column(Numeric(20, 4), comment="总资产收益率 ROA")

    debt_to_assets = Column(Numeric(20, 4), comment="资产负债率")
    current_ratio = Column(Numeric(20, 4), comment="流动比率")
    quick_ratio = Column(Numeric(20, 4), comment="速动比率")

    ocf = Column(Numeric(20, 4), comment="经营活动现金流净额")
    ocf_to_net_profit = Column(Numeric(20, 4), comment="经营现金流/净利润")
    free_cash_flow = Column(Numeric(20, 4), comment="自由现金流")

    ar_yoy = Column(Numeric(20, 4), comment="应收账款同比增长率")
    inventory_yoy = Column(Numeric(20, 4), comment="存货同比增长率")
    expense_ratio = Column(Numeric(20, 4), comment="期间费用率")

    revenue_quality_score = Column(Numeric(10, 4), comment="收入质量评分")
    profitability_score = Column(Numeric(10, 4), comment="盈利能力评分")
    solvency_score = Column(Numeric(10, 4), comment="偿债能力评分")
    cashflow_score = Column(Numeric(10, 4), comment="现金流质量评分")
    overall_score = Column(Numeric(10, 4), comment="综合评分")

    risk_flags = Column(JSONB, comment="风险标签列表")
    highlights = Column(JSONB, comment="亮点标签列表")
    metric_version = Column(String(20), nullable=False, default="v1", comment="指标版本号")

    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )


# =========================
# 7. 分析结果表
# =========================
class AnalysisResult(Base):
    __tablename__ = "analysis_result"

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    task_id = Column(String(64), nullable=False, comment="任务ID")
    ts_code = Column(String(20), nullable=False, comment="股票代码")
    analysis_type = Column(String(50), nullable=False, comment="分析类型")
    start_date = Column(Date, comment="分析起始日期")
    end_date = Column(Date, comment="分析结束日期")

    input_payload = Column(JSONB, nullable=False, comment="输入参数快照")
    metrics_snapshot = Column(JSONB, comment="分析时使用的指标快照")
    risk_assessment = Column(JSONB, comment="风险评估结果")
    insight_summary = Column(JSONB, comment="结构化洞察结论")
    agent_trace = Column(JSONB, comment="Agent 执行轨迹/调用链路")

    status = Column(String(20), nullable=False, default="success", comment="任务状态")
    model_name = Column(String(100), comment="使用的模型名称")
    prompt_version = Column(String(50), comment="提示词版本")

    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), comment="创建时间")


# =========================
# 8. 报告快照表
# =========================
class ReportSnapshot(Base):
    __tablename__ = "report_snapshot"

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    task_id = Column(String(64), nullable=False, comment="任务ID")
    ts_code = Column(String(20), nullable=False, comment="股票代码")
    report_type = Column(String(50), nullable=False, comment="报告类型")
    title = Column(String(255), nullable=False, comment="报告标题")

    summary = Column(Text, comment="报告摘要")
    report_content = Column(Text, nullable=False, comment="报告正文")
    report_markdown = Column(Text, comment="Markdown 格式报告")
    report_json = Column(JSONB, comment="结构化 JSON 报告")

    reviewer_status = Column(String(20), nullable=False, default="draft", comment="审核状态")
    reviewer_comment = Column(Text, comment="审核意见")

    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )


# =========================
# 9. 审计日志
# =========================
class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    task_id = Column(String(64), comment="任务ID")

    entity_type = Column(String(50), nullable=False, comment="实体类型")
    entity_id = Column(String(64), comment="实体ID")

    action = Column(String(50), nullable=False, comment="操作类型")
    operator = Column(String(100), nullable=False, default="system", comment="操作人")

    detail = Column(JSONB, comment="详细信息")

    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), comment="创建时间")