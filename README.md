# FinancialAnalyst

Project structure for a multi-agent financial analysis application.

## Layout

```text
FinancialAnalyst
©À©¤©¤ app/
©¦   ©À©¤©¤ api/
©¦   ©¦   ©À©¤©¤ routes.py
©¦   ©¦   ©¸©¤©¤ deps.py
©¦   ©À©¤©¤ agents/
©¦   ©¦   ©À©¤©¤ supervisor_agent.py
©¦   ©¦   ©À©¤©¤ data_agent.py
©¦   ©¦   ©À©¤©¤ analysis_agent.py
©¦   ©¦   ©À©¤©¤ report_agent.py
©¦   ©¦   ©¸©¤©¤ reflection_agent.py
©¦   ©À©¤©¤ workflows/
©¦   ©¦   ©À©¤©¤ graph.py
©¦   ©¦   ©À©¤©¤ state.py
©¦   ©¦   ©¸©¤©¤ nodes.py
©¦   ©À©¤©¤ skills/
©¦   ©¦   ©À©¤©¤ financial_data_skills.py
©¦   ©¦   ©À©¤©¤ analysis_skills.py
©¦   ©¦   ©À©¤©¤ report_skills.py
©¦   ©¦   ©¸©¤©¤ reflection_skills.py
©¦   ©À©¤©¤ tools/
©¦   ©¦   ©À©¤©¤ financial_data_tools.py
©¦   ©¦   ©À©¤©¤ metric_tools.py
©¦   ©¦   ©À©¤©¤ report_tools.py
©¦   ©¦   ©¸©¤©¤ persistence_tools.py
©¦   ©À©¤©¤ services/
©¦   ©¦   ©À©¤©¤ tushare_service.py
©¦   ©¦   ©À©¤©¤ financial_analysis_service.py
©¦   ©¦   ©À©¤©¤ metric_engine_service.py
©¦   ©¦   ©¸©¤©¤ report_service.py
©¦   ©À©¤©¤ repositories/
©¦   ©¦   ©À©¤©¤ company_repo.py
©¦   ©¦   ©À©¤©¤ income_repo.py
©¦   ©¦   ©À©¤©¤ balance_repo.py
©¦   ©¦   ©À©¤©¤ cashflow_repo.py
©¦   ©¦   ©À©¤©¤ indicator_repo.py
©¦   ©¦   ©À©¤©¤ derived_metrics_repo.py
©¦   ©¦   ©À©¤©¤ analysis_result_repo.py
©¦   ©¦   ©¸©¤©¤ report_snapshot_repo.py
©¦   ©À©¤©¤ models/
©¦   ©¦   ©À©¤©¤ db_models.py
©¦   ©¦   ©¸©¤©¤ schemas.py
©¦   ©À©¤©¤ core/
©¦   ©¦   ©À©¤©¤ config.py
©¦   ©¦   ©¸©¤©¤ database.py
©¦   ©À©¤©¤ prompts/
©¦   ©¦   ©À©¤©¤ supervisor.txt
©¦   ©¦   ©À©¤©¤ analysis.txt
©¦   ©¦   ©À©¤©¤ report.txt
©¦   ©¦   ©¸©¤©¤ reflection.txt
©¦   ©¸©¤©¤ main.py
©À©¤©¤ scripts/
©¦   ©À©¤©¤ init_db.py
©¦   ©À©¤©¤ sync_company_data.py
©¦   ©À©¤©¤ compute_metrics.py
©¦   ©¸©¤©¤ seed_companies.py
©À©¤©¤ tests/
©¸©¤©¤ README.md
```

## Notes

- `app/agents` keeps agent-facing orchestration logic.
- `app/workflows` defines graph, nodes, and runtime state.
- `app/skills` groups reusable business capabilities for agents.
- `app/tools` contains low-level helper functions.
- `app/services` and `app/repositories` separate domain logic from persistence access.
