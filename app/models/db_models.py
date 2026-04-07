"""数据库模型定义"""

from sqlalchemy.orm import declarative_base
from sqlalchemy import (
    Column, BigInteger, String, Boolean, Date, TIMESTAMP,
    Numeric, Text, JSON
)
from sqlalchemy.sql import func

Base = declarative_base()

# =========================
# 1. 公司维表
# =========================
class Company(Base):
    __tablename__ = "dim_company"

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    ts_code = Column(String(20), unique=True, nullable=False, comment="Tushare股票代码")
    symbol = Column(String(10), comment="股票短代码")
    name = Column(String(100), nullable=False, comment="公司名称")
    area = Column(String(50), comment="地区")
    industry = Column(String(100), comment="行业")
    market = Column(String(50), comment="市场类型（主板/创业板等）")
    exchange = Column(String(20), comment="交易所")
    list_date = Column(Date, comment="上市日期")

    is_active = Column(Boolean, default=True, comment="是否有效")

    source = Column(String(50), default="tushare", comment="数据来源")
    created_at = Column(TIMESTAMP, server_default=func.now(), comment="创建时间")
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), comment="更新时间")


# =========================
# 2. 利润表
# =========================
class Income(Base):
    __tablename__ = "fact_income"

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

    operate_profit = Column(Numeric(20, 4), comment="营业利润")
    total_profit = Column(Numeric(20, 4), comment="利润总额")

    income_tax = Column(Numeric(20, 4), comment="所得税费用")

    net_profit = Column(Numeric(20, 4), comment="净利润")
    n_income_attr_p = Column(Numeric(20, 4), comment="归母净利润")

    update_flag = Column(String(10), comment="更新标志")

    source = Column(String(50), default="tushare", comment="数据来源")
    created_at = Column(TIMESTAMP, server_default=func.now(), comment="创建时间")
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), comment="更新时间")


# =========================
# 3. 资产负债表
# =========================
class BalanceSheet(Base):
    __tablename__ = "fact_balance_sheet"

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    ts_code = Column(String(20), nullable=False, comment="股票代码")

    ann_date = Column(Date, comment="公告日期")
    f_ann_date = Column(Date, comment="实际公告日期")
    end_date = Column(Date, nullable=False, comment="报告期")

    total_assets = Column(Numeric(20, 4), comment="资产总计")
    total_liab = Column(Numeric(20, 4), comment="负债合计")

    money_cap = Column(Numeric(20, 4), comment="货币资金")
    accounts_receiv = Column(Numeric(20, 4), comment="应收账款")
    inventories = Column(Numeric(20, 4), comment="存货")

    total_cur_assets = Column(Numeric(20, 4), comment="流动资产合计")
    total_cur_liab = Column(Numeric(20, 4), comment="流动负债合计")

    total_hldr_eqy_exc_min_int = Column(Numeric(20, 4), comment="归母股东权益")

    update_flag = Column(String(10), comment="更新标志")

    source = Column(String(50), default="tushare", comment="数据来源")
    created_at = Column(TIMESTAMP, server_default=func.now(), comment="创建时间")
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), comment="更新时间")


# =========================
# 4. 现金流量表
# =========================
class CashFlow(Base):
    __tablename__ = "fact_cashflow"

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    ts_code = Column(String(20), nullable=False, comment="股票代码")

    ann_date = Column(Date, comment="公告日期")
    f_ann_date = Column(Date, comment="实际公告日期")
    end_date = Column(Date, nullable=False, comment="报告期")

    n_cashflow_act = Column(Numeric(20, 4), comment="经营活动现金流净额")
    n_cashflow_inv_act = Column(Numeric(20, 4), comment="投资活动现金流净额")
    n_cash_flows_fnc_act = Column(Numeric(20, 4), comment="筹资活动现金流净额")

    n_incr_cash_cash_equ = Column(Numeric(20, 4), comment="现金净增加额")
    c_cash_equ_end_period = Column(Numeric(20, 4), comment="期末现金余额")

    update_flag = Column(String(10), comment="更新标志")

    source = Column(String(50), default="tushare", comment="数据来源")
    created_at = Column(TIMESTAMP, server_default=func.now(), comment="创建时间")
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), comment="更新时间")


# =========================
# 5. 财务指标表
# =========================
class FinaIndicator(Base):
    __tablename__ = "fact_fina_indicator"

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    ts_code = Column(String(20), nullable=False, comment="股票代码")
    ann_date = Column(Date, comment="公告日期")
    end_date = Column(Date, nullable=False, comment="报告期")

    eps = Column(Numeric(20, 4), comment="每股收益")
    gross_margin = Column(Numeric(20, 4), comment="毛利率")
    netprofit_margin = Column(Numeric(20, 4), comment="净利率")

    roe = Column(Numeric(20, 4), comment="净资产收益率ROE")
    roa = Column(Numeric(20, 4), comment="总资产收益率ROA")

    debt_to_assets = Column(Numeric(20, 4), comment="资产负债率")

    update_flag = Column(String(10), comment="更新标志")

    source = Column(String(50), default="tushare", comment="数据来源")
    created_at = Column(TIMESTAMP, server_default=func.now(), comment="创建时间")
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), comment="更新时间")


# =========================
# 6. 派生指标表（核心）
# =========================
class DerivedMetrics(Base):
    __tablename__ = "fact_derived_metrics"

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    ts_code = Column(String(20), nullable=False, comment="股票代码")
    end_date = Column(Date, nullable=False, comment="报告期")

    revenue_yoy = Column(Numeric(20, 4), comment="营收同比")
    net_profit_yoy = Column(Numeric(20, 4), comment="净利润同比")

    gross_margin = Column(Numeric(20, 4), comment="毛利率")
    net_margin = Column(Numeric(20, 4), comment="净利率")

    roe = Column(Numeric(20, 4), comment="ROE")

    debt_to_assets = Column(Numeric(20, 4), comment="资产负债率")

    ocf_to_net_profit = Column(Numeric(20, 4), comment="经营现金流/净利润")

    risk_flags = Column(JSON, comment="风险标签列表")
    highlights = Column(JSON, comment="亮点标签列表")

    created_at = Column(TIMESTAMP, server_default=func.now(), comment="创建时间")
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), comment="更新时间")


# =========================
# 7. 分析结果表
# =========================
class AnalysisResult(Base):
    __tablename__ = "analysis_result"

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    task_id = Column(String(64), nullable=False, comment="任务ID")
    ts_code = Column(String(20), nullable=False, comment="股票代码")

    analysis_type = Column(String(50), comment="分析类型")

    input_payload = Column(JSON, comment="输入参数")
    metrics_snapshot = Column(JSON, comment="指标快照")
    risk_assessment = Column(JSON, comment="风险评估")
    insight_summary = Column(JSON, comment="结构化结论")

    status = Column(String(20), default="success", comment="状态")
    created_at = Column(TIMESTAMP, server_default=func.now(), comment="创建时间")


# =========================
# 8. 报告表
# =========================
class ReportSnapshot(Base):
    __tablename__ = "report_snapshot"

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    task_id = Column(String(64), nullable=False, comment="任务ID")
    ts_code = Column(String(20), nullable=False, comment="股票代码")

    title = Column(String(255), comment="报告标题")

    summary = Column(Text, comment="摘要")
    report_content = Column(Text, comment="正文")

    reviewer_status = Column(String(20), default="draft", comment="审核状态")

    created_at = Column(TIMESTAMP, server_default=func.now(), comment="创建时间")


# =========================
# 9. 审计日志
# =========================
class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    task_id = Column(String(64), comment="任务ID")

    entity_type = Column(String(50), comment="实体类型")
    entity_id = Column(String(64), comment="实体ID")

    action = Column(String(50), comment="操作类型")
    operator = Column(String(100), default="system", comment="操作人")

    detail = Column(JSON, comment="详细信息")

    created_at = Column(TIMESTAMP, server_default=func.now(), comment="创建时间")
