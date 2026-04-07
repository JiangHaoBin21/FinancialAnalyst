# -*- coding: utf-8 -*-
"""初始化数据库."""
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://admin:admin123@localhost:5432/finance_db"

engine = create_engine(DATABASE_URL)

create_table_statements = [
    """
    CREATE TABLE dim_company (
        id BIGSERIAL PRIMARY KEY,
        ts_code VARCHAR(20) NOT NULL UNIQUE,
        symbol VARCHAR(10),
        name VARCHAR(100) NOT NULL,
        area VARCHAR(50),
        industry VARCHAR(100),
        market VARCHAR(50),
        exchange VARCHAR(20),
        list_date DATE,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        source VARCHAR(50) NOT NULL DEFAULT 'tushare',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE fact_income (
        id BIGSERIAL PRIMARY KEY,
        ts_code VARCHAR(20) NOT NULL,
        ann_date DATE,
        f_ann_date DATE,
        end_date DATE NOT NULL,
        report_type VARCHAR(20),
        comp_type VARCHAR(20),

        basic_eps NUMERIC(20, 4),
        diluted_eps NUMERIC(20, 4),
        total_revenue NUMERIC(20, 4),
        revenue NUMERIC(20, 4),
        total_cogs NUMERIC(20, 4),
        oper_cost NUMERIC(20, 4),
        sell_exp NUMERIC(20, 4),
        admin_exp NUMERIC(20, 4),
        fin_exp NUMERIC(20, 4),
        assets_impair_loss NUMERIC(20, 4),
        invest_income NUMERIC(20, 4),
        operate_profit NUMERIC(20, 4),
        total_profit NUMERIC(20, 4),
        income_tax NUMERIC(20, 4),
        net_profit NUMERIC(20, 4),
        n_income_attr_p NUMERIC(20, 4),
        minority_gain NUMERIC(20, 4),
        oth_compr_income NUMERIC(20, 4),
        compr_inc_attr_p NUMERIC(20, 4),

        update_flag VARCHAR(10),
        source VARCHAR(50) NOT NULL DEFAULT 'tushare',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

        CONSTRAINT uq_fact_income UNIQUE (ts_code, end_date, report_type)
    );
    """,
    """
    CREATE TABLE fact_balance_sheet (
        id BIGSERIAL PRIMARY KEY,
        ts_code VARCHAR(20) NOT NULL,
        ann_date DATE,
        f_ann_date DATE,
        end_date DATE NOT NULL,
        report_type VARCHAR(20),
        comp_type VARCHAR(20),

        total_share NUMERIC(20, 4),
        money_cap NUMERIC(20, 4),
        trad_asset NUMERIC(20, 4),
        notes_receiv NUMERIC(20, 4),
        accounts_receiv NUMERIC(20, 4),
        oth_receiv NUMERIC(20, 4),
        prepayment NUMERIC(20, 4),
        inventories NUMERIC(20, 4),
        total_cur_assets NUMERIC(20, 4),
        fix_assets NUMERIC(20, 4),
        total_nca NUMERIC(20, 4),
        total_assets NUMERIC(20, 4),

        short_term_borr NUMERIC(20, 4),
        notes_payable NUMERIC(20, 4),
        acct_payable NUMERIC(20, 4),
        adv_receipts NUMERIC(20, 4),
        total_cur_liab NUMERIC(20, 4),
        bond_payable NUMERIC(20, 4),
        total_ncl NUMERIC(20, 4),
        total_liab NUMERIC(20, 4),

        total_hldr_eqy_exc_min_int NUMERIC(20, 4),
        total_hldr_eqy_inc_min_int NUMERIC(20, 4),

        update_flag VARCHAR(10),
        source VARCHAR(50) NOT NULL DEFAULT 'tushare',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

        CONSTRAINT uq_fact_balance_sheet UNIQUE (ts_code, end_date, report_type)
    );
    """,
    """
    CREATE TABLE fact_cashflow (
        id BIGSERIAL PRIMARY KEY,
        ts_code VARCHAR(20) NOT NULL,
        ann_date DATE,
        f_ann_date DATE,
        end_date DATE NOT NULL,
        report_type VARCHAR(20),
        comp_type VARCHAR(20),

        c_fr_sale_sg NUMERIC(20, 4),
        recp_tax_rends NUMERIC(20, 4),
        n_depos_incr_fi NUMERIC(20, 4),
        c_paid_goods_s NUMERIC(20, 4),
        c_paid_to_for_empl NUMERIC(20, 4),
        c_paid_for_taxes NUMERIC(20, 4),
        n_cashflow_act NUMERIC(20, 4),

        c_disp_withdrwl_invest NUMERIC(20, 4),
        c_recp_return_invest NUMERIC(20, 4),
        n_cashflow_inv_act NUMERIC(20, 4),

        c_recp_borrow NUMERIC(20, 4),
        proc_issue_bonds NUMERIC(20, 4),
        c_prepay_amt_borr NUMERIC(20, 4),
        c_pay_dist_dpcp_int_exp NUMERIC(20, 4),
        n_cash_flows_fnc_act NUMERIC(20, 4),

        n_incr_cash_cash_equ NUMERIC(20, 4),
        c_cash_equ_beg_period NUMERIC(20, 4),
        c_cash_equ_end_period NUMERIC(20, 4),

        update_flag VARCHAR(10),
        source VARCHAR(50) NOT NULL DEFAULT 'tushare',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

        CONSTRAINT uq_fact_cashflow UNIQUE (ts_code, end_date, report_type)
    );
    """,
    """
    CREATE TABLE fact_fina_indicator (
        id BIGSERIAL PRIMARY KEY,
        ts_code VARCHAR(20) NOT NULL,
        ann_date DATE,
        end_date DATE NOT NULL,

        eps NUMERIC(20, 4),
        dt_eps NUMERIC(20, 4),
        total_revenue_ps NUMERIC(20, 4),
        revenue_ps NUMERIC(20, 4),
        capital_rese_ps NUMERIC(20, 4),
        surplus_rese_ps NUMERIC(20, 4),
        undist_profit_ps NUMERIC(20, 4),

        extra_item NUMERIC(20, 4),
        profit_dedt NUMERIC(20, 4),
        gross_margin NUMERIC(20, 4),
        current_ratio NUMERIC(20, 4),
        quick_ratio NUMERIC(20, 4),
        cash_ratio NUMERIC(20, 4),
        invturn_days NUMERIC(20, 4),
        arturn_days NUMERIC(20, 4),
        inv_turn NUMERIC(20, 4),
        ar_turn NUMERIC(20, 4),
        ca_turn NUMERIC(20, 4),
        fa_turn NUMERIC(20, 4),
        assets_turn NUMERIC(20, 4),

        op_income NUMERIC(20, 4),
        valuechange_income NUMERIC(20, 4),
        interst_income NUMERIC(20, 4),
        daa NUMERIC(20, 4),
        ebit NUMERIC(20, 4),
        ebitda NUMERIC(20, 4),
        fcff NUMERIC(20, 4),
        fcfe NUMERIC(20, 4),

        current_exint NUMERIC(20, 4),
        noncurrent_exint NUMERIC(20, 4),
        interestdebt NUMERIC(20, 4),
        netdebt NUMERIC(20, 4),
        tangible_asset NUMERIC(20, 4),
        working_capital NUMERIC(20, 4),
        networking_capital NUMERIC(20, 4),
        invest_capital NUMERIC(20, 4),
        retained_earnings NUMERIC(20, 4),

        diluted2_eps NUMERIC(20, 4),
        bps NUMERIC(20, 4),
        ocfps NUMERIC(20, 4),
        retainedps NUMERIC(20, 4),
        cfps NUMERIC(20, 4),
        ebit_ps NUMERIC(20, 4),
        fcff_ps NUMERIC(20, 4),
        fcfe_ps NUMERIC(20, 4),

        netprofit_margin NUMERIC(20, 4),
        grossprofit_margin NUMERIC(20, 4),
        cogs_of_sales NUMERIC(20, 4),
        expense_of_sales NUMERIC(20, 4),
        profit_to_gr NUMERIC(20, 4),
        saleexp_to_gr NUMERIC(20, 4),
        adminexp_of_gr NUMERIC(20, 4),
        finaexp_of_gr NUMERIC(20, 4),
        impai_ttm NUMERIC(20, 4),
        gc_of_gr NUMERIC(20, 4),
        op_of_gr NUMERIC(20, 4),
        ebit_of_gr NUMERIC(20, 4),

        roe NUMERIC(20, 4),
        roe_waa NUMERIC(20, 4),
        roe_dt NUMERIC(20, 4),
        roa NUMERIC(20, 4),
        npta NUMERIC(20, 4),
        roic NUMERIC(20, 4),
        roe_yearly NUMERIC(20, 4),
        roa2_yearly NUMERIC(20, 4),

        debt_to_assets NUMERIC(20, 4),
        assets_to_eqt NUMERIC(20, 4),
        dp_assets_to_eqt NUMERIC(20, 4),

        update_flag VARCHAR(10),
        source VARCHAR(50) NOT NULL DEFAULT 'tushare',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

        CONSTRAINT uq_fact_fina_indicator UNIQUE (ts_code, end_date)
    );
    """,
    """
    CREATE TABLE fact_derived_metrics (
        id BIGSERIAL PRIMARY KEY,
        ts_code VARCHAR(20) NOT NULL,
        end_date DATE NOT NULL,

        revenue_yoy NUMERIC(20, 4),
        revenue_cagr_3y NUMERIC(20, 4),
        net_profit_yoy NUMERIC(20, 4),
        net_profit_cagr_3y NUMERIC(20, 4),

        gross_margin NUMERIC(20, 4),
        net_margin NUMERIC(20, 4),
        roe NUMERIC(20, 4),
        roa NUMERIC(20, 4),

        debt_to_assets NUMERIC(20, 4),
        current_ratio NUMERIC(20, 4),
        quick_ratio NUMERIC(20, 4),

        ocf NUMERIC(20, 4),
        ocf_to_net_profit NUMERIC(20, 4),
        free_cash_flow NUMERIC(20, 4),

        ar_yoy NUMERIC(20, 4),
        inventory_yoy NUMERIC(20, 4),
        expense_ratio NUMERIC(20, 4),

        revenue_quality_score NUMERIC(10, 4),
        profitability_score NUMERIC(10, 4),
        solvency_score NUMERIC(10, 4),
        cashflow_score NUMERIC(10, 4),
        overall_score NUMERIC(10, 4),

        risk_flags JSONB,
        highlights JSONB,
        metric_version VARCHAR(20) NOT NULL DEFAULT 'v1',

        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

        CONSTRAINT uq_fact_derived_metrics UNIQUE (ts_code, end_date, metric_version)
    );
    """,
    """
    CREATE TABLE analysis_result (
        id BIGSERIAL PRIMARY KEY,
        task_id VARCHAR(64) NOT NULL,
        ts_code VARCHAR(20) NOT NULL,
        analysis_type VARCHAR(50) NOT NULL,
        start_date DATE,
        end_date DATE,

        input_payload JSONB NOT NULL,
        metrics_snapshot JSONB,
        risk_assessment JSONB,
        insight_summary JSONB,
        agent_trace JSONB,

        status VARCHAR(20) NOT NULL DEFAULT 'success',
        model_name VARCHAR(100),
        prompt_version VARCHAR(50),
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE report_snapshot (
        id BIGSERIAL PRIMARY KEY,
        task_id VARCHAR(64) NOT NULL,
        ts_code VARCHAR(20) NOT NULL,
        report_type VARCHAR(50) NOT NULL,
        title VARCHAR(255) NOT NULL,

        summary TEXT,
        report_content TEXT NOT NULL,
        report_markdown TEXT,
        report_json JSONB,

        reviewer_status VARCHAR(20) NOT NULL DEFAULT 'draft',
        reviewer_comment TEXT,

        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE audit_log (
        id BIGSERIAL PRIMARY KEY,
        task_id VARCHAR(64),
        entity_type VARCHAR(50) NOT NULL,
        entity_id VARCHAR(64),
        action VARCHAR(50) NOT NULL,
        operator VARCHAR(100) NOT NULL DEFAULT 'system',
        detail JSONB,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """
]

with engine.connect() as conn:
    for sql in create_table_statements:
        conn.execute(text(sql))
    conn.commit()

print("✅数据库初始化完成")
