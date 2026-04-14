"""TuShare 数据服务层

职责：
1. 调用 TuShare Pro 接口
2. 将返回的 DataFrame 标准化为项目内部可用的数据结构
3. 不负责数据库写入，不负责业务分析
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

import pandas as pd
import tushare as ts
from app.core.config import settings


@dataclass
class TushareServiceConfig:
    """TuShare 服务配置"""
    token: str


class TushareService:
    """TuShare Pro 服务

    已封装接口：
    - stock_basic
    - income
    - balancesheet
    - cashflow
    - fina_indicator
    """

    def __init__(self, config: TushareServiceConfig):
        if not config.token:
            raise ValueError("TuShare token 不能为空")
        self.config = config
        self.pro = ts.pro_api(config.token)

    # =========================
    # 公共辅助方法
    # =========================
    @staticmethod
    def _to_date(value: Any) -> Optional[date]:
        """将 YYYYMMDD / datetime / date / NaN 转为 date"""
        if value is None:
            return None
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        if pd.isna(value):
            return None

        text = str(value).strip()
        if not text:
            return None

        # 兼容 YYYYMMDD
        if len(text) == 8 and text.isdigit():
            return datetime.strptime(text, "%Y%m%d").date()

        # 兼容 YYYY-MM-DD
        try:
            return datetime.strptime(text, "%Y-%m-%d").date()
        except ValueError:
            return None

    @staticmethod
    def _to_decimal(value: Any) -> Optional[Decimal]:
        """将数值转为 Decimal，空值返回 None"""
        if value is None or pd.isna(value):
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return None

    @staticmethod
    def _clean_str(value: Any) -> Optional[str]:
        """清洗字符串字段"""
        if value is None or pd.isna(value):
            return None
        text = str(value).strip()
        return text if text else None

    @staticmethod
    def _df_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
        """DataFrame 转 records；空表返回空列表"""
        if df is None or df.empty:
            return []
        return df.to_dict(orient="records")

    @staticmethod
    def _pick(record: dict[str, Any], field: str) -> Any:
        """安全取字段"""
        return record.get(field)

    # =========================
    # 1. stock_basic -> dim_company
    # =========================
    def fetch_stock_basic(
        self,
        list_status: str = "L",
        ts_code: Optional[str] = None,
        name: Optional[str] = None,
        exchange: Optional[str] = None,
        market: Optional[str] = None,
        is_hs: Optional[str] = None,
    ) -> pd.DataFrame:
        """获取股票基础信息

        官方接口：stock_basic
        常见参数：list_status / exchange / market / is_hs
        """
        params: dict[str, Any] = {"list_status": list_status}
        if name:
            params["name"] = name
        if ts_code:
            params["ts_code"] = ts_code
        if exchange:
            params["exchange"] = exchange
        if market:
            params["market"] = market
        if is_hs:
            params["is_hs"] = is_hs

        fields = ",".join([
            "ts_code",
            "symbol",
            "name",
            "area",
            "industry",
            "market",
            "exchange",
            "list_date",
            "list_status",
        ])
        return self.pro.stock_basic(**params, fields=fields)

    def normalize_stock_basic(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        """将 stock_basic 标准化为 dim_company 可入库结构"""
        results: list[dict[str, Any]] = []

        for row in self._df_to_records(df):
            results.append({
                "ts_code": self._clean_str(self._pick(row, "ts_code")),
                "symbol": self._clean_str(self._pick(row, "symbol")),
                "name": self._clean_str(self._pick(row, "name")),
                "area": self._clean_str(self._pick(row, "area")),
                "industry": self._clean_str(self._pick(row, "industry")),
                "market": self._clean_str(self._pick(row, "market")),
                "exchange": self._clean_str(self._pick(row, "exchange")),
                "list_date": self._to_date(self._pick(row, "list_date")),
                "is_active": self._clean_str(self._pick(row, "list_status")) == "L",
                "source": "tushare",
            })
        return results

    # =========================
    # 2. income -> fact_income
    # =========================
    def fetch_income(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None,
        report_type: Optional[str] = None,
        comp_type: Optional[str] = None,
    ) -> pd.DataFrame:
        """获取利润表

        官方接口：income
        普通接口按单只股票获取历史数据
        """
        params: dict[str, Any] = {"ts_code": ts_code}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if period:
            params["period"] = period
        if report_type:
            params["report_type"] = report_type
        if comp_type:
            params["comp_type"] = comp_type

        fields = ",".join([
            "ts_code",
            "ann_date",
            "f_ann_date",
            "end_date",
            "report_type",
            "comp_type",
            "basic_eps",
            "diluted_eps",
            "total_revenue",
            "revenue",
            "total_cogs",
            "oper_cost",
            "sell_exp",
            "admin_exp",
            "fin_exp",
            "assets_impair_loss",
            "invest_income",
            "operate_profit",
            "total_profit",
            "income_tax",
            "net_profit",
            "n_income_attr_p",
            "minority_gain",
            "oth_compr_income",
            "compr_inc_attr_p",
            "update_flag",
        ])
        return self.pro.income(**params, fields=fields)

    def normalize_income(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        """将 income 标准化为 fact_income 可入库结构"""
        results: list[dict[str, Any]] = []

        numeric_fields = [
            "basic_eps", "diluted_eps", "total_revenue", "revenue", "total_cogs",
            "oper_cost", "sell_exp", "admin_exp", "fin_exp", "assets_impair_loss",
            "invest_income", "operate_profit", "total_profit", "income_tax",
            "net_profit", "n_income_attr_p", "minority_gain", "oth_compr_income",
            "compr_inc_attr_p",
        ]

        for row in self._df_to_records(df):
            item = {
                "ts_code": self._clean_str(row.get("ts_code")),
                "ann_date": self._to_date(row.get("ann_date")),
                "f_ann_date": self._to_date(row.get("f_ann_date")),
                "end_date": self._to_date(row.get("end_date")),
                "report_type": self._clean_str(row.get("report_type")),
                "comp_type": self._clean_str(row.get("comp_type")),
                "update_flag": self._clean_str(row.get("update_flag")),
                "source": "tushare",
            }
            for field in numeric_fields:
                item[field] = self._to_decimal(row.get(field))
            results.append(item)

        return results

    # =========================
    # 3. balancesheet -> fact_balance_sheet
    # =========================
    def fetch_balance_sheet(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None,
        report_type: Optional[str] = None,
        comp_type: Optional[str] = None,
    ) -> pd.DataFrame:
        """获取资产负债表

        官方接口：balancesheet
        """
        params: dict[str, Any] = {"ts_code": ts_code}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if period:
            params["period"] = period
        if report_type:
            params["report_type"] = report_type
        if comp_type:
            params["comp_type"] = comp_type

        fields = ",".join([
            "ts_code",
            "ann_date",
            "f_ann_date",
            "end_date",
            "report_type",
            "comp_type",
            "total_share",
            "money_cap",
            "trad_asset",
            "notes_receiv",
            "accounts_receiv",
            "oth_receiv",
            "prepayment",
            "inventories",
            "total_cur_assets",
            "fix_assets",
            "total_nca",
            "total_assets",
            "short_term_borr",
            "notes_payable",
            "acct_payable",
            "adv_receipts",
            "total_cur_liab",
            "bond_payable",
            "total_ncl",
            "total_liab",
            "total_hldr_eqy_exc_min_int",
            "total_hldr_eqy_inc_min_int",
            "update_flag",
        ])
        return self.pro.balancesheet(**params, fields=fields)

    def normalize_balance_sheet(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        """将 balancesheet 标准化为 fact_balance_sheet 可入库结构"""
        results: list[dict[str, Any]] = []

        numeric_fields = [
            "total_share", "money_cap", "trad_asset", "notes_receiv",
            "accounts_receiv", "oth_receiv", "prepayment", "inventories",
            "total_cur_assets", "fix_assets", "total_nca", "total_assets",
            "short_term_borr", "notes_payable", "acct_payable", "adv_receipts",
            "total_cur_liab", "bond_payable", "total_ncl", "total_liab",
            "total_hldr_eqy_exc_min_int", "total_hldr_eqy_inc_min_int",
        ]

        for row in self._df_to_records(df):
            item = {
                "ts_code": self._clean_str(row.get("ts_code")),
                "ann_date": self._to_date(row.get("ann_date")),
                "f_ann_date": self._to_date(row.get("f_ann_date")),
                "end_date": self._to_date(row.get("end_date")),
                "report_type": self._clean_str(row.get("report_type")),
                "comp_type": self._clean_str(row.get("comp_type")),
                "update_flag": self._clean_str(row.get("update_flag")),
                "source": "tushare",
            }
            for field in numeric_fields:
                item[field] = self._to_decimal(row.get(field))
            results.append(item)

        return results

    # =========================
    # 4. cashflow -> fact_cashflow
    # =========================
    def fetch_cashflow(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None,
        report_type: Optional[str] = None,
        comp_type: Optional[str] = None,
    ) -> pd.DataFrame:
        """获取现金流量表

        官方接口：cashflow
        """
        params: dict[str, Any] = {"ts_code": ts_code}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if period:
            params["period"] = period
        if report_type:
            params["report_type"] = report_type
        if comp_type:
            params["comp_type"] = comp_type

        fields = ",".join([
            "ts_code",
            "ann_date",
            "f_ann_date",
            "end_date",
            "report_type",
            "comp_type",
            "c_fr_sale_sg",
            "recp_tax_rends",
            "n_depos_incr_fi",
            "c_paid_goods_s",
            "c_paid_to_for_empl",
            "c_paid_for_taxes",
            "n_cashflow_act",
            "c_disp_withdrwl_invest",
            "c_recp_return_invest",
            "n_cashflow_inv_act",
            "c_recp_borrow",
            "proc_issue_bonds",
            "c_prepay_amt_borr",
            "c_pay_dist_dpcp_int_exp",
            "n_cash_flows_fnc_act",
            "n_incr_cash_cash_equ",
            "c_cash_equ_beg_period",
            "c_cash_equ_end_period",
            "update_flag",
        ])
        return self.pro.cashflow(**params, fields=fields)

    def normalize_cashflow(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        """将 cashflow 标准化为 fact_cashflow 可入库结构"""
        results: list[dict[str, Any]] = []

        numeric_fields = [
            "c_fr_sale_sg", "recp_tax_rends", "n_depos_incr_fi", "c_paid_goods_s",
            "c_paid_to_for_empl", "c_paid_for_taxes", "n_cashflow_act",
            "c_disp_withdrwl_invest", "c_recp_return_invest", "n_cashflow_inv_act",
            "c_recp_borrow", "proc_issue_bonds", "c_prepay_amt_borr",
            "c_pay_dist_dpcp_int_exp", "n_cash_flows_fnc_act",
            "n_incr_cash_cash_equ", "c_cash_equ_beg_period", "c_cash_equ_end_period",
        ]

        for row in self._df_to_records(df):
            item = {
                "ts_code": self._clean_str(row.get("ts_code")),
                "ann_date": self._to_date(row.get("ann_date")),
                "f_ann_date": self._to_date(row.get("f_ann_date")),
                "end_date": self._to_date(row.get("end_date")),
                "report_type": self._clean_str(row.get("report_type")),
                "comp_type": self._clean_str(row.get("comp_type")),
                "update_flag": self._clean_str(row.get("update_flag")),
                "source": "tushare",
            }
            for field in numeric_fields:
                item[field] = self._to_decimal(row.get(field))
            results.append(item)

        return results

    # =========================
    # 5. fina_indicator -> fact_fina_indicator
    # =========================
    def fetch_fina_indicator(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None,
    ) -> pd.DataFrame:
        """获取财务指标

        官方接口：fina_indicator
        """
        params: dict[str, Any] = {"ts_code": ts_code}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if period:
            params["period"] = period

        # 这里只先取你当前库里已经建模的字段
        fields = ",".join([
            "ts_code",
            "ann_date",
            "end_date",
            "eps",
            "dt_eps",
            "total_revenue_ps",
            "revenue_ps",
            "capital_rese_ps",
            "surplus_rese_ps",
            "undist_profit_ps",
            "extra_item",
            "profit_dedt",
            "gross_margin",
            "current_ratio",
            "quick_ratio",
            "cash_ratio",
            "invturn_days",
            "arturn_days",
            "inv_turn",
            "ar_turn",
            "ca_turn",
            "fa_turn",
            "assets_turn",
            "op_income",
            "valuechange_income",
            "interst_income",
            "daa",
            "ebit",
            "ebitda",
            "fcff",
            "fcfe",
            "current_exint",
            "noncurrent_exint",
            "interestdebt",
            "netdebt",
            "tangible_asset",
            "working_capital",
            "networking_capital",
            "invest_capital",
            "retained_earnings",
            "diluted2_eps",
            "bps",
            "ocfps",
            "retainedps",
            "cfps",
            "ebit_ps",
            "fcff_ps",
            "fcfe_ps",
            "netprofit_margin",
            "grossprofit_margin",
            "cogs_of_sales",
            "expense_of_sales",
            "profit_to_gr",
            "saleexp_to_gr",
            "adminexp_of_gr",
            "finaexp_of_gr",
            "impai_ttm",
            "gc_of_gr",
            "op_of_gr",
            "ebit_of_gr",
            "roe",
            "roe_waa",
            "roe_dt",
            "roa",
            "npta",
            "roic",
            "roe_yearly",
            "roa2_yearly",
            "debt_to_assets",
            "assets_to_eqt",
            "dp_assets_to_eqt",
            "update_flag",
        ])
        return self.pro.fina_indicator(**params, fields=fields)

    def normalize_fina_indicator(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        """将 fina_indicator 标准化为 fact_fina_indicator 可入库结构"""
        results: list[dict[str, Any]] = []

        numeric_fields = [
            "eps", "dt_eps", "total_revenue_ps", "revenue_ps", "capital_rese_ps",
            "surplus_rese_ps", "undist_profit_ps", "extra_item", "profit_dedt",
            "gross_margin", "current_ratio", "quick_ratio", "cash_ratio",
            "invturn_days", "arturn_days", "inv_turn", "ar_turn", "ca_turn",
            "fa_turn", "assets_turn", "op_income", "valuechange_income",
            "interst_income", "daa", "ebit", "ebitda", "fcff", "fcfe",
            "current_exint", "noncurrent_exint", "interestdebt", "netdebt",
            "tangible_asset", "working_capital", "networking_capital",
            "invest_capital", "retained_earnings", "diluted2_eps", "bps",
            "ocfps", "retainedps", "cfps", "ebit_ps", "fcff_ps", "fcfe_ps",
            "netprofit_margin", "grossprofit_margin", "cogs_of_sales",
            "expense_of_sales", "profit_to_gr", "saleexp_to_gr", "adminexp_of_gr",
            "finaexp_of_gr", "impai_ttm", "gc_of_gr", "op_of_gr", "ebit_of_gr",
            "roe", "roe_waa", "roe_dt", "roa", "npta", "roic", "roe_yearly",
            "roa2_yearly", "debt_to_assets", "assets_to_eqt", "dp_assets_to_eqt",
        ]

        for row in self._df_to_records(df):
            item = {
                "ts_code": self._clean_str(row.get("ts_code")),
                "ann_date": self._to_date(row.get("ann_date")),
                "end_date": self._to_date(row.get("end_date")),
                "update_flag": self._clean_str(row.get("update_flag")),
                "source": "tushare",
            }
            for field in numeric_fields:
                item[field] = self._to_decimal(row.get(field))
            results.append(item)

        return results

    # =========================
    # 组合方法：方便上层直接调用
    # =========================
    def get_company_records(
        self,
        list_status: str = "L",
        ts_code: Optional[str] = None,
        name: Optional[str] = None,
        exchange: Optional[str] = None,
        market: Optional[str] = None,
        is_hs: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """获取并标准化公司基础信息"""
        df = self.fetch_stock_basic(
            list_status=list_status,
            ts_code=ts_code,
            name=name,
            exchange=exchange,
            market=market,
            is_hs=is_hs,
        )
        return self.normalize_stock_basic(df)

    def get_income_records(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None,
        report_type: Optional[str] = None,
        comp_type: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """获取并标准化利润表记录"""
        df = self.fetch_income(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            period=period,
            report_type=report_type,
            comp_type=comp_type,
        )
        return self.normalize_income(df)

    def get_balance_sheet_records(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None,
        report_type: Optional[str] = None,
        comp_type: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """获取并标准化资产负债表记录"""
        df = self.fetch_balance_sheet(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            period=period,
            report_type=report_type,
            comp_type=comp_type,
        )
        return self.normalize_balance_sheet(df)

    def get_cashflow_records(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None,
        report_type: Optional[str] = None,
        comp_type: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """获取并标准化现金流量表记录"""
        df = self.fetch_cashflow(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            period=period,
            report_type=report_type,
            comp_type=comp_type,
        )
        return self.normalize_cashflow(df)

    def get_fina_indicator_records(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """获取并标准化财务指标记录"""
        df = self.fetch_fina_indicator(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            period=period,
        )
        return self.normalize_fina_indicator(df)

if __name__ == "__main__":
    config = TushareServiceConfig(token=settings.TuShare_Token)
    print(type(config),config)
    pro = TushareService(config)
    print(pro.get_company_records(),len(pro.get_company_records()))
