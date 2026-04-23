from typing import Any


class CompanyProfileFetchSkill:
    def __init__(self, company_resolver, session_factory):
        self.company_resolver = company_resolver
        self.session_factory = session_factory

    def fetch(self, company_name: str | None, ts_code: str | None) -> dict[str, Any]:
        with self.session_factory() as db:
            company_profile = self.company_resolver.resolve(db, company_name, ts_code)
            db.commit()
        return company_profile