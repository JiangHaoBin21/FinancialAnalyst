# FinancialAnalyst

FinancialAnalyst 是一个面向 A 股上市公司的多 Agent 财务分析原型项目。当前系统以 LangGraph 工作流为核心，结合 OpenAI 兼容的大模型接口、TuShare Pro 数据源、PostgreSQL/SQLAlchemy 持久化层，推进从用户问题理解、任务规划、数据准备、证据收集、结构化分析到 Markdown 报告生成的端到端链路。

> 当前项目仍处于开发阶段。截至 2026-05-23，规划、数据准备、完整性检查、回源补数、分析证据工具、结构化分析和报告生成链路已经基本打通；ReflectionAgent、API 服务化入口、快照持久化和部分早期脚本仍需继续完善。

## 当前能力

- `SupervisorAgent + PlanningSkill` 调用 LLM，将自然语言请求解析为结构化任务计划，并支持缺失信息补问。
- `SupervisorReviewSkill` 在 Data、Analysis、Report、Reflection 等阶段后做流程层审查，决定继续、回退、补数据、等待用户输入或进入错误态。
- `DataAgent` 通过 LLM 规划所需数据分片，并在数据不完整时规划是否回源补数。
- `DataSubgraph` 使用 LangGraph 将利润表、资产负债表、现金流量表和财务指标分片并行抓取，再统一合并、检查完整性和 finalize。
- `CompanyResolver` 优先查询本地 `dim_company`，找不到时调用 TuShare 回源并落库。
- `DataPreparationSkill` 优先读取本地 PostgreSQL，发现缺失且回源计划允许时按报告期调用 TuShare 并 upsert。
- `AnalysisAgent` 已不再是简单 mock：它通过 ReAct 工具调用，从利润表、资产负债表、现金流量表、财务指标和跨报表诊断工具中收集证据，再由 LLM 生成结构化 `analysis_result`。
- `ReportAgent` 已不再是简单 mock：它基于 `analysis_result` 生成结构化 `report_result` 和完整 `markdown_report`，并要求保留数据限制、风险提示和免责声明。
- 工作流在 Report 阶段会把 `markdown_report` 保存到 `outputs/reports/`。

## 工作流概览

```text
用户问题
  -> SupervisorAgent
     -> PlanningSkill
        -> LLM 生成 JSON 计划
        -> Parser/Policy 校验、兜底、补全
  -> DataSubgraph
     -> DataAgent 规划 required_data_parts
     -> CompanyProfileFetchSkill 解析公司画像
     -> 并行抓取 income / balance / cashflow / fina_indicator
     -> 合并数据
     -> CompletenessCheckSkill 检查缺失报告期
     -> BackfillPlanSkill 判断是否需要 TuShare 回源
     -> Data finalize
  -> SupervisorReviewSkill 审查 Data 产物
  -> AnalysisAgent
     -> ReAct 调用证据工具
     -> LLM 生成结构化 analysis_result
  -> SupervisorReviewSkill 审查 Analysis 产物
  -> ReportAgent
     -> LLM 生成结构化 report_result
     -> 输出 markdown_report
     -> 保存 Markdown 文件到 outputs/reports/
  -> SupervisorReviewSkill 审查 Report 产物
  -> ReflectionAgent 复核（当前为最小通过逻辑）
  -> finished
```

## 项目结构

```text
FinancialAnalyst/
├── app/
│   ├── agents/              # Supervisor/Data/Analysis/Report/Reflection Agent
│   ├── api/                 # 路由和 schema 占位，当前不是完整 Web 服务
│   ├── core/                # 配置和数据库连接
│   ├── domain/              # 规划、时间范围、完整性检查等领域对象
│   ├── exceptions/          # 数据阶段异常
│   ├── llms/                # OpenAI 兼容 LLM 客户端
│   ├── models/              # SQLAlchemy ORM 模型和轻量 schema
│   ├── repositories/        # 公司、三大报表、财务指标、结果快照等数据访问层
│   ├── services/            # TuShare、指标、报告、持久化等服务
│   ├── skills/
│   │   ├── analysis/        # 报表证据工具、跨表诊断工具、指标分组和注册表
│   │   ├── capabilities/    # 公司解析、时间解析、完整性检查等基础能力
│   │   ├── data/            # 数据分片规划、公司画像、数据准备、回源规划
│   │   └── supervisor/      # 规划 prompt/parser/policy、Supervisor 审查技能
│   ├── tools/               # 早期工具函数，部分仍是占位实现
│   ├── utils/               # 报告文件写入、日期工具等
│   ├── workflows/
│   │   ├── subgraphs/       # DataSubgraph 节点和路由
│   │   ├── graph.py         # 主 LangGraph 门面
│   │   ├── nodes.py         # 主阶段节点
│   │   └── state.py         # WorkflowState 和状态工具
│   └── main.py              # 最小应用描述入口
├── docs/
│   └── subagent_contracts.md
├── scripts/
│   ├── init_db.py
│   ├── test_planner.py
│   ├── test_data_preparation_skill.py
│   ├── test_data_preparation_flow.py
│   ├── test_supervisor_data_analysis_nodes.py
│   └── run_demo.py          # 早期调试入口，接口可能落后于当前 Agent 构造方式
├── tests/
├── requirements.txt
└── README.md
```

## 运行环境

建议使用 Python 3.10+，并准备：

- PostgreSQL 数据库
- TuShare Pro Token
- 一个兼容 OpenAI Chat Completions API 的大模型服务

当前配置从项目根目录 `.env` 读取：

```env
DATABASE_URL=postgresql://user:password@localhost:5432/finance_db
TUSHARE_TOKEN=your_tushare_token
XIAOMI_API_KEY=your_api_key
XIAOMI_MODEL_NAME=your_model_name
XIAOMI_BASE_URL=https://api.example.com/v1/
```

说明：代码内部部分字段仍沿用 `deepseek_*` 命名，但实际读取的是 `XIAOMI_API_KEY`、`XIAOMI_MODEL_NAME`、`XIAOMI_BASE_URL`。

安装依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

初始化数据库：

```powershell
python scripts/init_db.py
```

数据库模型以 `app/models/db_models.py` 为准，主要表包括：

- `dim_company`
- `fact_income`
- `fact_balance_sheet`
- `fact_cashflow`
- `fact_fina_indicator`
- `fact_derived_metrics`
- `analysis_result`
- `report_snapshot`
- `audit_log`

注意：`scripts/init_db.py` 是手工建表脚本，适合快速初始化。当前 ORM 字段扩展较快，已有数据库需要自行迁移或使用集成脚本中的 schema 检查确认表结构是否匹配。

## 常用脚本

查看最小应用描述：

```powershell
python app/main.py
```

测试规划链路：

```powershell
python scripts/test_planner.py
```

测试公司解析、本地数据读取、完整性检查和 TuShare 回源流程：

```powershell
python scripts/test_data_preparation_skill.py
python scripts/test_data_preparation_flow.py
```

运行当前最完整的真实集成检查：

```powershell
python scripts/test_supervisor_data_analysis_nodes.py
```

该脚本会使用真实 `OpenAIClient`、真实数据库、真实 TuShare 服务，覆盖 Supervisor、Data、Analysis 和 Report 阶段，并打印 Analysis ReAct 阶段的 tool calls。运行前必须确保 `.env`、数据库和外部服务可用。

部分早期脚本仍待同步最新构造参数和依赖注入方式，例如 `scripts/run_demo.py`、`scripts/sync_company_data.py`、`scripts/seed_companies.py`。使用前应先检查当前 Agent/Service 构造函数。

## 核心模块

### Supervisor 层

`app/skills/supervisor/` 负责规划和流程审查：

- `planning_prompt_builder.py` 构造规划 prompt。
- `planning_parser.py` 从 LLM 输出中提取 JSON，并校验 `PlanningResult`。
- `planning_policy.py` 对规划结果做规则兜底、默认时间范围、默认 task plan 和语义校验。
- `planning_skill.py` 串联 prompt、LLM、parser、policy。
- `review_skill.py` 在每个大阶段完成后做流程层准入审查。

规划结果会写入 `WorkflowState`，核心字段包括 `task_type`、`company_name`、`ts_code`、`time_range`、`analysis_focus`、`output_mode`、`task_plan`、`missing_fields` 和 `next_step`。

### Data 层

Data 阶段拆成主 `DataAgent` 和确定性 DataSubgraph 节点：

- `RequiredPartsSkill` 使用 LLM 判断需要哪些数据分片。
- `CompanyProfileFetchSkill` 通过 `CompanyResolver` 获取公司画像。
- `DataPreparationSkill` 按时间范围和分片查询本地库，必要时回源 TuShare 并 upsert。
- `CompletenessCheckSkill` 检查请求期间内每个数据分片的报告期覆盖情况。
- `BackfillPlanSkill` 根据完整性检查结果判断是否需要补拉缺失报告期。

当前支持的数据分片：

- `income_statements`
- `balance_sheets`
- `cashflow_statements`
- `financial_indicators`

### Analysis 层

`AnalysisAgent` 分两阶段工作：

1. ReAct 证据收集：根据用户问题、分析重点和可用数据，动态调用证据工具。
2. Finalize：只基于已收集 evidence 生成结构化 `analysis_result`。

已实现的证据工具包括：

- `income_statement_evidence_tool`
- `balance_sheet_evidence_tool`
- `cashflow_statement_evidence_tool`
- `fina_indicator_evidence_tool`
- `cross_statement_evidence_tool`

`analysis_result` 主要字段：

- `status`
- `summary`
- `overall_score`
- `dimensions`
- `data_limitations`
- `evidence`
- `conclusion`

### Report 层

`ReportAgent` 基于 `analysis_result` 生成结构化 `report_result`，不重新计算指标、不新增财务事实、不覆盖 AnalysisAgent 的核心判断。

`report_result` 主要字段：

- `status`
- `report_type`
- `title`
- `executive_summary`
- `overall_assessment`
- `sections`
- `risk_warnings`
- `data_limitations`
- `conclusion`
- `disclaimer`
- `markdown_report`

工作流会调用 `app/utils/report_file_writer.py`，将 `markdown_report` 保存为：

```text
outputs/reports/report_<报告标题>_<时间戳>.md
```

### Reflection 层

`ReflectionAgent` 当前仍是最小实现：默认审查通过，并返回空 issue/suggestion。后续需要补充正式的报告质量检查、数据引用一致性检查和回退路由建议。

### API 和 Tools

`app/api/` 当前只提供轻量路由/schema 占位，不是可直接启动的 FastAPI/Flask 服务。

`app/tools/` 中仍有部分早期占位函数，和当前 Agent 主链路不是完全同一套抽象，后续需要清理或并入正式技能层。

## 开发状态

已基本成型：

- LangGraph 主工作流和 DataSubgraph
- `WorkflowState` JSON-safe 状态收敛和执行历史记录
- Supervisor 规划、规则兜底、阶段审查和路由
- 数据分片规划、并行抓取、合并、完整性检查、回源补数
- TuShare 标准化服务和 PostgreSQL Repository 层
- 利润表、资产负债表、现金流、财务指标、跨报表诊断证据工具
- Analysis ReAct tool-calling 和结构化分析输出
- Report 结构化 JSON 和 Markdown 报告生成
- Markdown 报告文件落盘
- 真实集成检查脚本 `scripts/test_supervisor_data_analysis_nodes.py`

仍需完善：

- ReflectionAgent 的真实质量审查、问题归因和重试/回退策略
- API 服务化入口
- `analysis_result`、`report_snapshot` 等结果快照的工作流内持久化
- 默认 `build_workflow_graph()` 和早期脚本的依赖注入一致性
- 数据库 schema 迁移机制
- `tests/` 下正式单元测试和集成测试体系
- 早期 services/tools 与当前 Agent/Skill 主链路的抽象收敛

## 注意事项

- `.env` 包含数据库、TuShare 和大模型密钥，不要提交真实凭据。
- 真实集成脚本会访问外部 LLM、数据库和 TuShare，运行成本和网络可用性需要自行确认。
- `outputs/reports/` 是报告生成产物目录，不属于核心源码。
- `__pycache__/` 和脚本输出文件可能在本地运行后出现，提交前应清理或加入忽略规则。
