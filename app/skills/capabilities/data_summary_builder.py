class DataSummaryBuilder:
    def build(
        self,
        company_profile: dict,
        financial_data: dict,
        requested_time_range,
        normalized_start_date: str | None,
        normalized_end_date: str | None,
        company_source: str,
        financial_data_sources: dict[str, str],
        completeness,
    ) -> dict:
        ...