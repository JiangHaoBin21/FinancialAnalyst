# FinancialAnalyst

FinancialAnalyst 是一个面向 A 股上市公司的多 Agent 财务分析原型项目。当前代码以 LangGraph 工作流为核心，结合 OpenAI 兼容的大模型接口、TuShare 数据源、PostgreSQL/SQLAlchemy 持久化层，实现从用户问题理解、任务规划、财务数据准备到报告生成的端到端骨架。

> 当前项目仍处于开发阶段：规划、数据获取、数据库模型和数据完整性检查链路已经有较完整实现；分析、报告和复核 Agent 目前还是 mock/占位逻辑。

## 核心能力

- 使用 `SupervisorAgent + PlanningSkill` 调用大模型，将用户自然语言请求解析为结构化任务计划。
- 使用 `DataAgent` 根据分析焦点选择所需数据分片，例如公司画像、利润表、资产负债表、现金流量表和财务指标。
- 使用 LangGraph 编排工作流，并支持财务数据分片节点并行执行。
- 使用 TuShare Pro 获取并标准化公司基础信息、利润表、资产负债表、现金流量表和财务指标数据。
- 使用 SQLAlchemy Repository 层访问 PostgreSQL，支持查询、批量创建和按业务唯一键 upsert。
- 使用数据准备与完整性检查能力，优先读取本地库，发现缺失后可按期间从 TuShare 回补并落库。
- 提供基础的分析、报告、复核 Agent，用于验证工作流主干。

## 工作流概览

```text
用户问题
  -> SupervisorAgent
     -> PlanningSkill
        -> LLM 生成 JSON 计划
        -> Parser/Policy 校验、兜底和补全
  -> DataAgent 规划 required_data_parts
  -> 公司解析 CompanyResolver
     -> 本地 dim_company
     -> TuShare 回源
  -> DataPreparationSkill
     -> 本地财务表查询
     -> 缺失期间 TuShare 回补
  -> CompletenessCheckSkill 数据完整性检查
  -> AnalysisAgent 生成分析结果（当前为 mock）
  -> ReportAgent 生成报告草稿（当前为 mock）
  -> ReflectionAgent 复核报告（当前为 mock）
```

## 项目结构

```text
FinancialAnalyst/
├── app/
│   ├── agents/              # Supervisor/Data/Analysis/Report/Reflection Agent
│   ├── api/                 # 简单 API 路由占位，不是完整 Web 服务
│   ├── core/                # 配置和数据库连接
│   ├── domain/              # 规划、时间范围、数据完整性等领域对象
│   ├── llms/                # OpenAI 兼容 LLM 客户端抽象与实现
│   ├── models/              # SQLAlchemy ORM 模型和简单 schema
│   ├── repositories/        # 公司、三大报表、指标、结果快照等数据访问层
│   ├── services/            # TuShare、指标计算、报告服务
│   ├── skills/
│   │   ├── capabilities/    # 公司解析、时间范围解析、完整性检查等基础能力
│   │   ├── data/            # 公司画像、数据准备、回补计划等数据技能
│   │   └── planning/        # 规划 prompt、parser、policy 和技能入口
│   ├── tools/               # 指标、报告、数据访问等工具函数
│   ├── workflows/           # LangGraph 状态、节点和图构建逻辑
│   └── main.py              # 最小应用描述入口
├── docs/
│   └── subagent_contracts.md
├── scripts/
│   ├── init_db.py
│   ├── test_data_preparation_skill.py
│   ├── test_data_preparation_flow.py
│   ├── test_planner.py
│   └── run_demo.py
├── tests/
├── requirements.txt
└── README.md
```

## 运行环境

建议使用 Python 3.10+，并准备 PostgreSQL 数据库、TuShare Token，以及一个 OpenAI 兼容的大模型服务。

项目从 `.env` 读取以下配置：

```env
DATABASE_URL=postgresql://user:password@localhost:5432/finance_db
TUSHARE_TOKEN=your_tushare_token
DEEPSEEK_API_KEY=your_api_key
DEEPSEEK_MODEL_NAME=your_model_name
DEEPSEEK_BASE_URL=https://api.example.com/v1/
```

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

该脚本会创建以下主要表：

- `dim_company`
- `fact_income`
- `fact_balance_sheet`
- `fact_cashflow`
- `fact_fina_indicator`
- `fact_derived_metrics`
- `analysis_result`
- `report_snapshot`
- `audit_log`

## 常用脚本

```powershell
# 测试 LLM 规划链路
python scripts/test_planner.py

# 测试公司解析和本地财务数据读取
python scripts/test_data_preparation_skill.py

# 测试数据读取、完整性检查和 TuShare 回补流程
python scripts/test_data_preparation_flow.py

# 查看最小应用描述
python app/main.py
```

`scripts/run_demo.py` 用于调试完整工作流，但完整执行依赖 LLM、数据库、TuShare 和数据技能配置，当前更适合作为开发参考。

## 主要模块说明

### 规划层

`app/skills/planning/` 负责构造规划 prompt、解析大模型 JSON 输出，并通过 policy 做兜底和业务校验。规划结果会写入 `WorkflowState`，包括：

- `task_type`
- `company_name` / `ts_code`
- `time_range`
- `analysis_focus`
- `output_mode`
- `task_plan`
- `missing_fields`

### 工作流层

`app/workflows/` 定义 LangGraph 状态、节点和路由逻辑。`WorkflowGraph` 支持：

- `run(user_query)` 启动新任务
- `continue_from_state(state)` 从已有状态继续执行
- `resume_with_user_input(state, user_input)` 在缺少信息时恢复执行
- `step_once(state)` 单步调试节点

### 数据层

数据准备链路由以下模块协作：

- `CompanyResolver`：优先从本地 `dim_company` 查公司信息，查不到则调用 TuShare 并落库。
- `DataPreparationSkill`：按时间范围和数据分片读取本地财务表，必要时回补 TuShare 数据。
- `DataCompletenessChecker`：生成季度期末列表，检查各数据表是否覆盖用户请求期间。
- `repositories/*`：封装各表的查询、创建、更新和 upsert 逻辑。

### 服务层

`TushareService` 已封装以下 TuShare Pro 接口，并将 DataFrame 标准化为项目内部记录：

- `stock_basic`
- `income`
- `balancesheet`
- `cashflow`
- `fina_indicator`

### Agent 层

- `SupervisorAgent`：调用规划技能，决定是否需要用户补充信息，以及下一步执行哪个 Agent。
- `DataAgent`：根据用户问题和分析焦点选择所需数据分片。
- `AnalysisAgent`：当前输出简单 mock 分析结果。
- `ReportAgent`：当前输出简单 Markdown mock 报告。
- `ReflectionAgent`：当前默认复核通过。

## 开发状态

已实现或基本成型：

- LangGraph 工作流骨架
- 规划 prompt/parser/policy
- OpenAI 兼容 LLM 客户端
- TuShare 数据拉取与标准化
- PostgreSQL 表结构与 ORM 模型
- Repository 数据访问层
- 公司解析、本地数据读取、完整性检查、缺失数据回补

仍需完善：

- AnalysisAgent 的真实财务指标计算和结论生成
- ReportAgent 的正式报告结构、引用数据和可解释输出
- ReflectionAgent 的质量检查与重规划机制
- API 层服务化入口
- 脚本和工作流之间的依赖注入一致性
- 单元测试和集成测试覆盖

## 注意事项

- `.env` 中包含数据库、TuShare 和大模型密钥，应避免提交真实凭据。
- `app/api/` 当前只是路由和 schema 占位，不提供可直接启动的 FastAPI/Flask 服务。
- 部分早期脚本仍是占位或调试入口，使用前应确认构造参数和当前服务接口一致。
