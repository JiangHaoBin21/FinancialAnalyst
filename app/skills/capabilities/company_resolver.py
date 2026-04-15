"""通过公司名称或股票代码返回完整公司信息"""

from typing import Any

from sqlalchemy.exc import MultipleResultsFound
from sqlalchemy.orm import Session
from app.exceptions.data_exception import MultiRecordException, CompanyNotFoundError


class CompanyResolver:
    def __init__(self, company_repo, tushare_service):
        self.company_repo = company_repo
        self.tushare_service = tushare_service

    def resolve(
        self,
        db: Session,
        company_name: str | None,
        ts_code: str | None,
    ) -> dict[str, Any]:
        company = None
        if ts_code:
            company = self.company_repo.get_by_ts_code(db, ts_code)
        elif company_name:
            try:
                company = self.company_repo.get_by_name(db, company_name)
            except MultipleResultsFound as e:
                raise MultiRecordException("数据库中存在重复的公司名称，请给出完整的股票代码") from e

        if company:
           return {
               "company_name": company.name,
               "ts_code": company.ts_code,
               "symbol": company.symbol,
               "industry": company.industry,
               "area": company.area,
               "market": company.market,
               "exchange": company.exchange,
               "list_date": company.list_date,
               "source": "db"
           }
        else:
            ts_company = self._resolve_from_tushare(db, company_name, ts_code)
            if ts_company:
                return {
                    "company_name": ts_company["name"],
                    "ts_code": ts_company["ts_code"],
                    "symbol": ts_company["symbol"],
                    "industry": ts_company["industry"],
                    "area": ts_company["area"],
                    "market": ts_company["market"],
                    "exchange": ts_company["exchange"],
                    "list_date": ts_company["list_date"],
                    "source": ts_company["source"]
                }
            else:
                raise CompanyNotFoundError("多渠道均未找到匹配公司，请检查公司名称或股票代码")


    def _resolve_from_tushare(self, db: Session, company_name: str | None, ts_code: str | None) -> dict[str, Any] | None:
        """当本地数据库查询不到记录时，从TuShare拉取对应数据并更新数据库"""
        company = self.tushare_service.get_company_records(name=company_name, ts_code=ts_code)
        if company:
            result = self.company_repo.upsert_by_ts_code(db, company[0])
            return company[0]
        else:
            return None

