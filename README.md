# 📊 FinancialAnalyst

FinancialAnalyst 是一个面向 A 股上市公司的多 Agent 财务分析项目。系统以
`LangGraph` 为流程编排核心，组合 OpenAI 兼容大模型、TuShare Pro 数据源和
PostgreSQL/SQLAlchemy 数据层，将自然语言问题转换为数据准备、证据分析、报告生成与质量审查流程。

> **项目状态（基于 2026-05-26 源码核对）**
> Supervisor、Data、Analysis、Report 与基于 LLM 的 Reflection 链路已在集成脚本中装配；
> FastAPI 路由与应用层 Runner 已落地。项目仍处于开发阶段，默认图装配、可选依赖、
> 数据库迁移和结果快照持久化仍需要继续收敛，详见下文“已知限制”。

## ✨ 核心能力

| 能力 | 说明 | 当前实现 |
| --- | --- | --- |
| 任务规划 | 将公司、时间范围、分析重点和输出方式解析为任务计划 | `SupervisorAgent`、`PlanningSkill` |
| 流程审查 | 每个主阶段完成后判断继续、回退、补数或失败 | `SupervisorReviewSkill` |
| 数据准备 | 公司解析、本地查询、完整性检查与 TuShare 回源补数 | `DataAgent`、`DataSubgraph` |
| 财务证据分析 | 通过 ReAct tool calling 从多类财务数据中收集证据 | `AnalysisAgent` |
| 报告生成 | 生成结构化结果与正式 Markdown 报告 | `ReportAgent` |
| 报告质检 | 检查报告忠实性、风险披露、结构与可交付性 | `ReflectionAgent` |
| 接口层 | 健康检查与同步分析请求路由 | FastAPI、`FinancialAnalysisRunner` |
| 可恢复执行 | 工作流支持注入 LangGraph checkpointer 与 `thread_id` | `WorkflowGraph` |

## 🔄 工作流

```text
用户问题
  -> SupervisorAgent
     -> PlanningSkill：LLM 规划 + parser/policy 校验与兜底
  -> DataSubgraph
     -> DataAgent：规划 required_data_parts
     -> CompanyProfileFetchSkill：解析公司画像
     -> 并行抓取 income / balance / cashflow / fina_indicator
     -> CompletenessCheckSkill：检查报告期覆盖
     -> BackfillPlanSkill：必要时回源 TuShare 并落库
     -> Data finalize
  -> SupervisorReviewSkill：审查 Data 产物
  -> AnalysisAgent
     -> ReAct 调用财务证据工具
     -> 输出 analysis_result
  -> SupervisorReviewSkill：审查 Analysis 产物
  -> ReportAgent
     -> 输出 report_result 与 markdown_report
     -> 保存 outputs/reports/report_<标题>_<时间戳>.md
  -> SupervisorReviewSkill：审查 Report 产物
  -> ReflectionAgent：报告质量复核与路由建议
  -> SupervisorReviewSkill：消费复核结论并决定完成或回退
  -> finished / error / await_user_input
```

### 数据分片

Data 阶段当前支持以下核心财务分片：

| 分片 | 数据内容 |
| --- | --- |
| `income_statements` | 利润表 |
| `balance_sheets` | 资产负债表 |
| `cashflow_statements` | 现金流量表 |
| `financial_indicators` | TuShare 财务指标 |

### 分析证据工具

`AnalysisAgent` 可调用的证据工具包括：

- `income_statement_evidence_tool`
- `balance_sheet_evidence_tool`
- `cashflow_statement_evidence_tool`
- `fina_indicator_evidence_tool`
- `cross_statement_evidence_tool`

## 🧰 技术栈

| 分类 | 技术 |
| --- | --- |
| 工作流编排 | LangGraph |
| 大模型接入 | OpenAI Python SDK，支持 OpenAI 兼容 Chat Completions API |
| 财务数据源 | TuShare Pro |
| 数据存储 | PostgreSQL、SQLAlchemy |
| HTTP 接口 | FastAPI |
| 输出格式 | 结构化 JSON、Markdown 报告 |

## 🚀 快速开始

### 1. 环境准备

建议使用 **Python 3.10+**，并准备：

- 可连接的 PostgreSQL 数据库。
- 可用的 TuShare Pro Token。
- 一个支持 Chat Completions 的 OpenAI 兼容模型服务。

### 2. 安装基础依赖

Windows PowerShell 示例：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

当前 `requirements.txt` 覆盖主工作流使用的核心依赖，但尚未包含所有可选入口依赖：

```powershell
# 启动 FastAPI 接口时需要
python -m pip install fastapi uvicorn

# 运行 PostgreSQL checkpoint 示例脚本时需要
python -m pip install langgraph-checkpoint-postgres "psycopg[binary,pool]"
```

### 3. 配置环境变量

在项目根目录创建或维护 `.env`：

```env
DATABASE_URL=postgresql://user:password@localhost:5432/finance_db
TUSHARE_TOKEN=your_tushare_token
XIAOMI_API_KEY=your_api_key
XIAOMI_MODEL_NAME=your_model_name
XIAOMI_BASE_URL=https://api.example.com/v1/
```

> `OpenAIClientConfig` 内部字段仍沿用 `deepseek_*` 命名，但当前实际读取的是
> `XIAOMI_API_KEY`、`XIAOMI_MODEL_NAME` 和 `XIAOMI_BASE_URL`。

### 4. 初始化数据库

```powershell
python scripts/init_db.py
```

`scripts/init_db.py` 使用直接 `CREATE TABLE` 语句，适合初始化空数据库；它不是迁移工具。
已有表结构发生变化时，应先核对 ORM 模型或自行执行迁移，而不是重复运行该脚本。

### 5. 运行端到端集成检查

当前覆盖最完整、并且显式装配各 Agent 依赖的入口是：

```powershell
python scripts/test_supervisor_data_analysis_nodes.py --help
python scripts/test_supervisor_data_analysis_nodes.py --query "请分析 300750.SZ 在 2023 年的财务表现，并生成正式报告。"
```

该脚本会：

- 使用真实 `OpenAIClient` 进行规划、阶段审查、分析、报告生成和最终复核。
- 使用本地 PostgreSQL，并在需要时访问 TuShare 补充数据。
- 检查主图及 DataSubgraph 的阶段产物和 JSON 安全性。
- 将生成的 Markdown 报告写入 `outputs/reports/`。

运行会产生外部模型调用成本，并可能写入数据库和报告文件。

## 🌐 API 入口

项目已定义 FastAPI 应用及以下路由：

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| `GET` | `/health` | 健康检查 |
| `POST` | `/api/v1/financial-analysis` | 同步执行一次财务分析任务 |

安装接口依赖后，可启动服务并验证健康检查：

```powershell
python -m uvicorn app.main:app --reload
Invoke-RestMethod http://127.0.0.1:8000/health
```

请求体定义如下：

```json
{
  "query": "请分析宁德时代 2023 年的财务表现并生成报告",
  "thread_id": "optional-thread-id",
  "include_state": false
}
```

接口采用同步阻塞方式执行工作流。当前 `POST /api/v1/financial-analysis` 的默认 Runner
依赖默认工作流装配，而该装配仍存在 Reflection 依赖参数未同步的问题；在修复该装配或
显式注入正确节点之前，应以完整集成脚本作为主链路验证入口。

## 🗃️ 数据存储与产物

### 数据库表

ORM 模型及初始化脚本覆盖以下主要表：

| 表名 | 用途 |
| --- | --- |
| `dim_company` | 公司基础信息 |
| `fact_income` | 利润表数据 |
| `fact_balance_sheet` | 资产负债表数据 |
| `fact_cashflow` | 现金流量表数据 |
| `fact_fina_indicator` | 财务指标数据 |
| `fact_derived_metrics` | 衍生指标与评分预留 |
| `analysis_result` | 分析结果快照预留 |
| `report_snapshot` | 报告快照预留 |
| `audit_log` | 审计记录预留 |

### 报告输出

当 `ReportAgent` 完成报告生成后，工作流调用 `app/utils/report_file_writer.py`，
将 Markdown 文件写入：

```text
outputs/reports/report_<报告标题>_<时间戳>.md
```

当前可确认落盘的是 Markdown 报告文件；`analysis_result` 和 `report_snapshot`
的 Repository 仍是占位访问层，尚未接入主工作流持久化。

## 🗂️ 项目结构

```text
FinancialAnalyst/
├── app/
│   ├── agents/              # Supervisor / Data / Analysis / Report / Reflection Agents
│   ├── api/                 # FastAPI 路由与依赖
│   ├── application/         # FinancialAnalysisRunner 应用层入口
│   ├── core/                # 配置加载与数据库连接
│   ├── domain/              # 规划、时间范围、完整性等领域对象
│   ├── llms/                # OpenAI 兼容模型客户端
│   ├── models/              # 请求响应 schema 与 SQLAlchemy ORM
│   ├── repositories/        # 公司及财务数据访问层
│   ├── services/            # TuShare 等服务；部分服务仍为早期占位
│   ├── skills/
│   │   ├── analysis/        # 财务证据工具与指标分组
│   │   ├── capabilities/    # 公司解析、时间解析、完整性检查
│   │   ├── data/            # 数据规划、读取、补数
│   │   └── supervisor/      # 任务规划与阶段审查
│   ├── utils/               # 报告文件写入等工具
│   ├── workflows/
│   │   ├── subgraphs/       # DataSubgraph 节点与路由
│   │   ├── graph.py         # 主工作流与 checkpointer 接口
│   │   ├── nodes.py         # 主阶段节点
│   │   └── state.py         # WorkflowState 和状态辅助函数
│   └── main.py              # FastAPI 应用入口
├── docs/
│   └── subagent_contracts.md
├── outputs/reports/         # 运行时生成的 Markdown 报告
├── scripts/                 # 初始化、检查、实验与 checkpoint 脚本
├── tests/                   # 待建设的正式测试目录
├── requirements.txt
└── README.md
```

## 🧪 脚本说明

| 脚本 | 用途 | 备注 |
| --- | --- | --- |
| `scripts/init_db.py` | 初始化业务表 | 面向空库，不是迁移工具 |
| `scripts/test_planner.py` | 调用 LLM 验证规划结果 | 需要模型配置 |
| `scripts/test_data_preparation_skill.py` | 验证公司解析和数据读取 | 需要数据库及 TuShare 配置 |
| `scripts/test_data_preparation_flow.py` | 验证完整性检查和补数流程 | 可能写入数据库 |
| `scripts/test_supervisor_data_analysis_nodes.py` | 完整真实链路检查 | 当前推荐的端到端入口 |
| `scripts/test_checkpoint.py` | 内存 checkpoint 示例 | 依赖默认图装配修复后使用 |
| `scripts/test_postgres_checkpoint.py` | PostgreSQL checkpoint 示例 | 包含固定示例连接串，使用前调整 |
| `scripts/test_read_postgres_checkpoint.py` | 读取 PostgreSQL checkpoint | 包含固定示例连接串，使用前调整 |
| `scripts/run_demo.py` | 早期演示入口 | 构造参数已落后于当前 Agents |
| `scripts/test_supervisor_data_nodes.py` | 早期 Data 链路检查 | 构造参数已落后于当前 Agents |
| `scripts/compute_metrics.py`、`seed_companies.py`、`sync_company_data.py` | 早期服务验证脚本 | 对应服务或 Repository 仍有占位实现 |

## ⚠️ 已知限制

- `app/workflows/graph.py` 默认构建路径仍以 `ReflectionAgent()` 初始化审查 Agent，
  而当前实现要求传入 `llm_client`；因此默认 Runner、API 分析请求和依赖该默认路径的
  checkpoint 示例在同步构造参数前不能作为可靠端到端入口。
- `requirements.txt` 尚未纳入 FastAPI/Uvicorn 与 PostgreSQL checkpoint 的可选依赖。
- `scripts/init_db.py` 没有迁移或幂等建表机制，ORM 变更后需人工管理 schema。
- 分析和报告快照表已建模，但主流程目前只确认写出 Markdown 报告文件。
- `tests/` 尚未形成正式的自动化测试套件；当前校验主要依赖 `scripts/` 中的真实集成脚本。
- `.gitignore` 当前仅忽略 `.idea` 与 `.env`；运行后生成的 `__pycache__/` 和
  `outputs/` 可能显示为未跟踪文件。

## 🔐 使用注意

- 不要提交包含真实数据库密码、TuShare Token 或模型 API Key 的 `.env`。
- 项目输出属于模型辅助财务分析结果，不构成投资建议。
- 真实链路会调用外部 LLM 与 TuShare，运行前应确认额度、网络及数据权限。
- 报告中的结论应结合数据完整性、审查结果和适用的业务场景进行复核。
