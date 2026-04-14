""""""

from typing import Any, Optional
from app.repositories.company_repo import CompanyRepository

class CompanyResolver:
    def resolve(
        self,
        company_name: str | None,
        ts_code: str | None,
    ) -> tuple[dict[str, Any], str]:
        """
        return:
        - company_profile
        - company_source: 'db' | 'tushare+persisted'
        """
        company_repo = CompanyRepository()
        if ts_code:
            company = company_repo.get_by_ts_code(ts_code)
