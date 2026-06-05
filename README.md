# FinancialAnalyst

FinancialAnalyst 是一个面向 A 股上市公司的多 Agent 财务分析项目。系统以 LangGraph 为工作流编排核心，连接 OpenAI 兼容大模型、TuShare Pro、PostgreSQL/SQLAlchemy 和 FastAPI，将自然语言问题转化为数据准备、财务证据分析、报告生成与质量审查流程。

项目当前同时包含：

- FastAPI 后端：提供健康检查和同步财务分析接口。
- LangGraph 多 Agent 工作流：Supervisor、Data、Analysis、Report、Reflection 分阶段协作。
- Vue + TypeScript + Vite 前端：提供一个可演示的 AI 财务分析工作台。
- PostgreSQL 数据层：存储公司基础信息、财务报表、指标与预留分析快照表。
- 脚本入口：用于初始化数据库、同步数据、检查规划、验证完整工作流和 checkpoint。

> 项目状态：已具备后端接口、默认工作流装配、真实数据/模型集成脚本和前端演示页面。当前 HTTP 分析接口仍是同步阻塞模式，完整报告生成可能耗时较长。

## 核心能力

| 能力 | 说明 | 主要实现 |
| --- | --- | --- |
| 任务规划 | 解析公司、时间范围、分析重点，生成多 Agent 执行计划 | `SupervisorAgent`、`PlanningSkill` |
| 阶段审查 | 每个主阶段完成后判断继续、回退、补数据或失败 | `SupervisorReviewSkill` |
| 数据准备 | 公司解析、本地查询、完整性检查、必要时 TuShare 回源补数 | `DataAgent`、`DataSubgraph` |
| 财务分析 | ReAct 风格调用财务证据工具，生成结构化分析结果 | `AnalysisAgent` |
| 报告生成 | 基于结构化分析生成正式报告和 Markdown 正文 | `ReportAgent` |
| 报告复核 | 检查报告忠实性、风险披露、数据限制和表达质量 | `ReflectionAgent` |
| API 服务 | 暴露健康检查和同步财务分析任务接口 | FastAPI、`FinancialAnalysisRunner` |
| 前端演示 | 任务输入、Agent 时间线、结果摘要、风险提示、Markdown 报告 | Vue、Vite、Tailwind CSS |
| 可恢复执行 | 支持 LangGraph checkpointer 和 `thread_id` | `WorkflowGraph`、PostgreSQL checkpoint |

## 工作流概览

```text
用户问题
  -> SupervisorAgent
     -> PlanningSkill 生成任务计划
  -> DataSubgraph
     -> DataAgent 规划 required_data_parts
     -> CompanyProfileFetchSkill 解析公司画像
     -> 并行准备 income / balance / cashflow / fina_indicator
     -> CompletenessCheckSkill 检查报告期覆盖
     -> BackfillPlanSkill 必要时回源 TuShare 并落库
     -> Data finalize
  -> SupervisorReviewSkill 审查 Data 产物
  -> AnalysisAgent
     -> 调用财务证据工具
     -> 输出 analysis_result
  -> SupervisorReviewSkill 审查 Analysis 产物
  -> ReportAgent
     -> 输出 report_result 与 markdown_report
     -> 保存 outputs/reports/report_<标题>_<时间戳>.md
  -> SupervisorReviewSkill 审查 Report 产物
  -> ReflectionAgent 复核报告质量
  -> SupervisorReviewSkill 消费复核结论
  -> finished / error / await_user_input
```

### 数据分片

| 分片 | 数据内容 |
| --- | --- |
| `company_profile` | 公司基础信息 |
| `income_statements` | 利润表 |
| `balance_sheets` | 资产负债表 |
| `cashflow_statements` | 现金流量表 |
| `financial_indicators` | TuShare 财务指标 |

### 分析证据工具

`AnalysisAgent` 当前可使用以下证据工具：

- `income_statement_evidence_tool`
- `balance_sheet_evidence_tool`
- `cashflow_statement_evidence_tool`
- `fina_indicator_evidence_tool`
- `cross_statement_evidence_tool`

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 后端 API | FastAPI、Uvicorn、Pydantic v2 |
| 工作流 | LangGraph、LangGraph PostgreSQL checkpoint |
| 大模型 | OpenAI Python SDK，支持 OpenAI 兼容 Chat Completions API |
| 数据源 | TuShare Pro |
| 数据库 | PostgreSQL、SQLAlchemy、psycopg、psycopg2 |
| 前端 | Vue 3、TypeScript、Vite、Tailwind CSS |
| 前端库 | axios、markdown-it、lucide-vue-next |
| 报告输出 | 结构化 JSON、Markdown |

## 快速开始

### 1. 环境准备

建议使用：

- Python 3.10+
- Node.js 18+
- PostgreSQL
- TuShare Pro Token
- OpenAI 兼容模型服务

### 2. 安装后端依赖

Windows PowerShell 示例：

```powershell
cd E:\PythonProjects\FinancialAnalyst
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

当前 `requirements.txt` 已包含 FastAPI、Uvicorn、LangGraph、PostgreSQL checkpoint、TuShare、SQLAlchemy、OpenAI SDK 等后端依赖。

### 3. 配置后端环境变量

在项目根目录创建或维护 `.env`：

```env
DATABASE_URL=postgresql://user:password@localhost:5432/finance_db
TUSHARE_TOKEN=your_tushare_token
XIAOMI_API_KEY=your_api_key
XIAOMI_MODEL_NAME=your_model_name
XIAOMI_BASE_URL=https://api.example.com/v1/
```

说明：

- `DATABASE_URL` 用于业务表和 LangGraph PostgreSQL checkpoint。
- `TUSHARE_TOKEN` 用于公司与财务数据查询/回源。
- `XIAOMI_*` 是当前代码读取的大模型配置变量名，底层通过 OpenAI 兼容客户端调用。

### 4. 初始化数据库

```powershell
python scripts/init_db.py
```

`scripts/init_db.py` 使用直接建表语句，适合初始化空数据库；它不是迁移工具。后续表结构变化时，请以 ORM 模型为准并自行管理迁移。

### 5. 启动后端

```powershell
python -m uvicorn app.main:app --reload
```

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

接口文档：

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/redoc`

### 6. 安装并启动前端

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

访问：

```text
http://127.0.0.1:5173/
```

PowerShell 在部分 Windows 环境会拦截 `npm.ps1`，使用 `npm.cmd` 更稳。

前端默认通过 Vite proxy 将 `/api` 和 `/health` 转发到 `http://127.0.0.1:8000`。也可以创建 `frontend/.env` 覆盖配置：

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_API_TIMEOUT_MS=0
```

`VITE_API_TIMEOUT_MS=0` 表示前端不主动中断请求。由于当前分析接口是同步长请求，建议保持为 `0`。

## API 说明

### GET `/health`

健康检查。

响应示例：

```json
{
  "status": "ok"
}
```

### POST `/api/v1/financial-analysis`

同步执行一次财务分析任务。

请求体：

```json
{
  "query": "请分析宁德时代 2023 年的财务表现并生成报告",
  "thread_id": "optional-thread-id",
  "include_state": false
}
```

字段说明：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `query` | `string` | 是 | 用户原始问题，最小长度为 1 |
| `thread_id` | `string \| null` | 否 | 可选线程 ID；不传时后端自动生成 |
| `include_state` | `boolean` | 否 | 是否尝试返回完整工作流状态，调试时使用 |

响应体：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `thread_id` | `string` | 本次工作流线程 ID |
| `status` | `string \| null` | 工作流状态，例如 `finished`、`error`、`needs_user_input` |
| `current_stage` | `string \| null` | 当前阶段 |
| `next_step` | `string \| null` | 下一步阶段 |
| `needs_user_input` | `boolean` | 是否需要用户补充信息 |
| `has_error` | `boolean` | 是否进入错误态 |
| `assistant_message` | `string \| null` | 面向用户的状态说明 |
| `error_message` | `string \| null` | 错误信息 |
| `final_report` | `string \| null` | 最终 Markdown 报告 |
| `analysis_result` | `object` | AnalysisAgent 结构化结果 |
| `report_result` | `object` | ReportAgent 结构化结果 |
| `execution_history` | `array` | Agent 执行轨迹 |

注意：

- 该接口目前是同步阻塞模式，完整工作流可能需要数分钟。
- 前端已将 axios 超时默认设为 `0`，用于等待长时间同步分析。
- 如果需要更好的用户体验，后续可扩展为“提交任务、查询状态、获取报告”的异步接口。

## 前端页面

前端位于 `frontend/`，首页即财务分析工作台：

- 顶部产品区：`Multi-Agent Financial Analysis Platform`
- 任务输入区：公司名称或股票代码、年份、分析问题、分析重点
- Agent 执行区：Supervisor、DataAgent、AnalysisAgent、ReportAgent、ReflectionAgent 时间线
- 结果摘要区：总体评分、评级标签、核心摘要、关键指标卡片
- 风险与限制：风险提示、数据限制
- 报告展示：使用 `markdown-it` 渲染 `markdown_report` 或 `final_report`

常用命令：

```powershell
cd frontend
npm.cmd run dev
npm.cmd run type-check
npm.cmd run build
npm.cmd run preview
```

## 数据库表

ORM 模型位于 `app/models/db_models.py`。

| 表名 | 用途 |
| --- | --- |
| `dim_company` | 公司基础信息 |
| `fact_income` | 利润表数据 |
| `fact_balance_sheet` | 资产负债表数据 |
| `fact_cashflow` | 现金流量表数据 |
| `fact_fina_indicator` | 财务指标数据 |
| `fact_derived_metrics` | 派生指标、评分、风险标签和亮点标签 |
| `analysis_result` | 分析结果快照预留 |
| `report_snapshot` | 报告快照预留 |
| `audit_log` | 审计日志预留 |

## 报告输出

当 `ReportAgent` 完成报告生成后，工作流会调用 `app/utils/report_file_writer.py`，将 Markdown 文件写入：

```text
outputs/reports/report_<报告标题>_<时间戳>.md
```

当前主流程已确认会写出 Markdown 报告文件；分析结果和报告快照表已建模，后续可继续接入更完整的结果持久化。

## 项目结构

```text
FinancialAnalyst/
├── app/
│   ├── agents/              # Supervisor / Data / Analysis / Report / Reflection Agents
│   ├── api/                 # FastAPI 路由与依赖
│   ├── application/         # FinancialAnalysisRunner 应用层入口
│   ├── core/                # 配置加载与数据库连接
│   ├── domain/              # 规划、时间范围、完整性等领域对象
│   ├── exceptions/          # 自定义异常
│   ├── llms/                # OpenAI 兼容模型客户端
│   ├── models/              # Pydantic schema 与 SQLAlchemy ORM
│   ├── prompts/             # Agent 提示词资源
│   ├── repositories/        # 公司及财务数据访问层
│   ├── services/            # TuShare、分析、报告与持久化服务
│   ├── skills/
│   │   ├── analysis/        # 财务证据工具与指标分组
│   │   ├── capabilities/    # 公司解析、时间解析、完整性检查
│   │   ├── data/            # 数据规划、读取、补数
│   │   └── supervisor/      # 任务规划与阶段审查
│   ├── tools/               # 报告、指标、持久化等工具函数
│   ├── utils/               # 报告文件写入等通用工具
│   ├── workflows/           # 主图、节点、状态和 DataSubgraph
│   └── main.py              # FastAPI 应用入口
├── docs/
│   └── subagent_contracts.md
├── frontend/
│   ├── src/
│   │   ├── api/             # 前端 API 封装
│   │   ├── components/      # 工作台组件
│   │   ├── pages/           # 页面组件
│   │   ├── types/           # TypeScript 类型
│   │   └── utils/           # 前端格式化工具
│   ├── package.json
│   └── vite.config.ts
├── outputs/reports/         # 运行时生成的 Markdown 报告
├── scripts/                 # 初始化、同步、检查和 checkpoint 脚本
├── requirements.txt
└── README.md
```

## 脚本说明

| 脚本 | 用途 | 备注 |
| --- | --- | --- |
| `scripts/init_db.py` | 初始化业务表 | 面向空库，不是迁移工具 |
| `scripts/seed_companies.py` | 写入示例公司数据 | 依赖数据库配置 |
| `scripts/sync_company_data.py` | 从 TuShare 同步公司基础信息 | 依赖 TuShare Token |
| `scripts/compute_metrics.py` | 早期派生指标计算入口 | 依赖当前服务实现 |
| `scripts/test_planner.py` | 调用真实 LLM 验证任务规划 | 需要模型配置 |
| `scripts/test_data_preparation_skill.py` | 验证数据准备能力 | 需要数据库和 TuShare |
| `scripts/test_data_preparation_flow.py` | 验证完整性检查和补数流程 | 可能写入数据库 |
| `scripts/test_supervisor_data_nodes.py` | 验证 Supervisor + Data 阶段 | 支持中文参数 |
| `scripts/test_supervisor_data_analysis_nodes.py` | 验证完整真实链路 | 当前推荐的端到端脚本 |
| `scripts/test_checkpoint.py` | checkpoint 基础示例 | 用于恢复能力验证 |
| `scripts/test_postgres_checkpoint.py` | PostgreSQL checkpoint 示例 | 使用前核对连接配置 |
| `scripts/test_read_postgres_checkpoint.py` | 读取 PostgreSQL checkpoint | 使用前核对连接配置 |
| `scripts/run_demo.py` | 早期演示入口 | 部分构造参数已落后于当前 Agent 签名 |

推荐端到端检查：

```powershell
python scripts/test_supervisor_data_analysis_nodes.py --help
python scripts/test_supervisor_data_analysis_nodes.py --query "请分析 300750.SZ 在 2023 年的财务表现，并生成正式报告。"
```

该脚本会调用真实 LLM、数据库和 TuShare，可能产生外部调用成本并写入数据库/报告文件。

## 开发验证

后端：

```powershell
python -m uvicorn app.main:app --reload
Invoke-RestMethod http://127.0.0.1:8000/health
```

前端：

```powershell
cd frontend
npm.cmd run type-check
npm.cmd run build
```

如果只想检查 API 预检/CORS，可在后端运行时访问前端开发服务并提交任务。后端当前允许：

- `http://127.0.0.1:5173`
- `http://localhost:5173`
- `http://127.0.0.1:4173`
- `http://localhost:4173`

## 已知限制与后续方向

- `POST /api/v1/financial-analysis` 是同步长请求，前端会持续 loading 等待完整响应；后续建议扩展异步任务接口。
- `include_state=true` 会让 Runner 生成完整 state，但当前 FastAPI `response_model` 不包含 `state` 字段，HTTP 响应可能过滤该字段。
- `scripts/init_db.py` 不是迁移工具，表结构演进需要单独管理。
- `analysis_result`、`report_snapshot` 等表已建模，但主链路当前重点仍是返回接口结果和写出 Markdown 报告。
- `scripts/run_demo.py` 等早期入口部分参数已落后，端到端验证优先使用 `test_supervisor_data_analysis_nodes.py`。
- 仓库当前可能产生 `frontend/node_modules/`、`frontend/dist/`、`__pycache__/`、`outputs/` 等运行产物，提交前请按团队策略清理或更新 `.gitignore`。

## 使用注意

- 不要提交真实数据库密码、TuShare Token 或模型 API Key。
- 真实链路会调用外部 LLM 与 TuShare，运行前请确认额度、网络和数据权限。
- 生成报告属于模型辅助财务分析结果，不构成投资建议。
- 报告结论应结合数据完整性、审查结果和业务场景进行人工复核。
