# Subagent Read/Write Contracts

本文件定义多 Agent 财务分析系统中各 Subagent 对 `WorkflowState` 的读写规范。

目标：
- 明确每个 Agent 的职责边界
- 规范 state 的读写行为
- 避免职责漂移 / 状态污染
- 支持后续扩展与调试

---

# 1. SupervisorAgent

## Purpose
解析用户请求，调用 PlanningSkill，初始化任务规划并写入 state。

---

## Reads
- user_query

---

## Writes
- task_type
- company_name
- ts_code
- time_range
- analysis_focus
- output_mode

- planner_message
- raw_planner_response

- needs_user_input
- missing_fields

- task_plan
- current_step_index

- current_stage
- next_step
- status

- assistant_message

---

## Must NOT Write
- company_profile
- financial_data
- data_summary

- analysis_result
- analysis_summary

- report_draft
- report_sections
- final_report

- reflection_result

---

## Success Criteria
- 成功解析用户意图
- 生成合法 task_plan
- 若信息完整 → status = READY_FOR_EXECUTION
- 若信息缺失 → status = NEEDS_USER_INPUT

---

## Failure Cases
- LLM 输出不可解析
- planning 结构不合法
- 关键字段缺失且未标记 needs_user_input

---

## Downstream Consumer
- Graph / Nodes（根据 task_plan 推进流程）

---

# 2. DataAgent

## Purpose
根据公司信息与时间范围，准备结构化财务数据。

---

## Reads
- company_name
- ts_code
- time_range
- task_type
- analysis_focus（可选）

---

## Writes
- company_profile
- financial_data
- data_summary

- assistant_message
- status
- next_step

- execution_history（通过 add_execution_record）

---

## Field Semantics

### company_profile
公司基础信息：
- company_name
- ts_code
- 行业 / 上市时间等（可扩展）

---

### financial_data
供 AnalysisAgent 使用的核心数据：
- income_statements
- balance_sheets
- cashflow_statements
- financial_indicators

⚠️ 只允许“数据”，不允许“结论”

---

### data_summary
数据准备情况摘要：
- years_covered
- has_missing_data
- 数据来源（mock / tushare / db）

---

## Must NOT Write
- analysis_result
- analysis_summary
- final_report
- reflection_result

---

## Success Criteria
- financial_data 非空
- data_summary 能说明数据覆盖情况
- 可进入 DATA → ANALYSIS 流程

---

## Failure Cases
- 找不到公司
- 数据为空或严重缺失
- 时间范围不合法

---

## Downstream Consumer
- AnalysisAgent

---

# 3. AnalysisAgent

## Purpose
对财务数据进行结构化分析，生成可复用的分析结果。

---

## Reads
- company_profile
- financial_data
- data_summary
- analysis_focus
- time_range

---

## Writes
- analysis_result
- analysis_summary

- assistant_message
- status
- next_step

- execution_history

---

## Field Semantics

### analysis_result（核心结构）

必须为结构化对象，推荐结构：

```json
{
  "growth": {
    "metrics": {},
    "findings": [],
    "summary": ""
  },
  "profitability": {
    "metrics": {},
    "findings": [],
    "summary": ""
  },
  "solvency": {
    "metrics": {},
    "findings": [],
    "summary": ""
  },
  "cashflow": {
    "metrics": {},
    "findings": [],
    "summary": ""
  },
  "risk_signals": [],
  "overall_conclusion": ""
}