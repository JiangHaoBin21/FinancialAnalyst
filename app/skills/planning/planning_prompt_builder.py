"""planning skill提示词构造"""

from datetime import datetime
from typing import Any, Optional

AGENT_REGISTRY: dict[str, dict[str, Any]] = {
    "DataAgent": {
        "responsibilities": [
            "识别当前任务需要哪些财务数据",
            "查询本地数据库是否已有目标公司数据",
            "必要时调用外部数据源（如 TuShare）拉取数据",
            "输出结构化财务数据结果",
        ],
        "cannot_do": [
            "不负责深度财务结论分析",
            "不负责生成最终面向用户的报告",
        ],
        "typical_actions": [
            "fetch_financial_data",
            "load_company_profile",
            "check_data_freshness",
            "sync_financial_statements",
        ],
    },
    "AnalysisAgent": {
        "responsibilities": [
            "基于已有财务数据做指标计算",
            "进行趋势分析、结构分析、风险识别",
            "输出结构化分析结论",
        ],
        "cannot_do": [
            "不负责原始数据拉取",
            "不负责最终报告排版输出",
        ],
        "typical_actions": [
            "analyze_financial_health",
            "analyze_profitability",
            "analyze_solvency",
            "analyze_growth",
            "identify_risks",
        ],
    },
    "ReportAgent": {
        "responsibilities": [
            "将分析结果组织成自然语言报告、摘要或结论",
            "根据用户要求输出详细报告或简要总结",
        ],
        "cannot_do": [
            "不负责原始财务数据拉取",
            "不负责底层指标计算",
        ],
        "typical_actions": [
            "generate_financial_report",
            "generate_summary",
            "draft_conclusion",
        ],
    },
    "ReflectionAgent": {
        "responsibilities": [
            "检查分析或报告是否存在遗漏、逻辑矛盾、证据不足",
            "提出修正建议，必要时要求回退重做",
        ],
        "cannot_do": [
            "不负责原始数据拉取",
        ],
        "typical_actions": [
            "review_analysis_result",
            "review_report_quality",
            "request_replan",
        ],
    },
}

def _render_agent_catalog() -> str:
    """
    将 AGENT_REGISTRY 渲染为 prompt 文本。
    """
    lines: list[str] = []

    for agent_name, meta in AGENT_REGISTRY.items():
        lines.append(f"{agent_name}:")
        responsibilities = meta.get("responsibilities", [])
        cannot_do = meta.get("cannot_do", [])
        typical_actions = meta.get("typical_actions", [])

        if responsibilities:
            lines.append("  - 职责：")
            for item in responsibilities:
                lines.append(f"    - {item}")

        if cannot_do:
            lines.append("  - 不负责：")
            for item in cannot_do:
                lines.append(f"    - {item}")

        if typical_actions:
            lines.append("  - 典型动作：")
            for item in typical_actions:
                lines.append(f"    - {item}")

        lines.append("")

    return "\n".join(lines).strip()

def _get_current_time():
    now = datetime.now()
    return {
        "year": now.year,
        "month": now.month
    }

def build_planning_prompt(user_query: str) -> str:
    """
    构造给大模型的规划提示词。
    """
    current_date = _get_current_time()

    agent_catalog_text = _render_agent_catalog()

    return f"""
你是一个多 Agent 财报分析系统中的规划器（Planning Skill）。

你的职责：
1. 理解用户任务意图
2. 提取关键任务参数
3. 生成高层执行计划 task_plan
4. 输出结构化 JSON 结果，供系统后续解析和校验

请注意：
- 你负责“任务理解和高层规划”
- 你不负责直接执行数据获取、分析、报告生成
- 你输出的是“规划建议”，系统代码会进一步校验并进入运行时调度
- 你的输出必须能被解析为合法 JSON 对象
- 允许使用 JSON 代码块包裹，但不要输出与 JSON 无关的额外说明文字

====================
【系统中的可用 Agent 及能力边界】
====================
{agent_catalog_text}

====================
【当前时间上下文】
====================
{{
"current_year": {current_date["year"]},
"current_month": {current_date["month"]}
}}
在处理类似“近三年”“最近一年”等时间表达时，请基于该日期进行推算。

====================
【规划规则】
====================
1. 如果用户想分析某家上市公司的财务情况、财报、年报、季报、经营表现、风险情况：
- task_type 设为 "financial_analysis"

2. 如果无法识别用户任务：
- task_type 设为 "unknown"

3. 如果用户明确要求“简单总结 / 简短结论 / 摘要”：
- output_mode 设为 "summary"
否则默认设为 "report"

4. 如果缺少执行任务所必需的信息，才设置：
- needs_user_input = true
- missing_fields 填写缺失字段名列表

5. time_range 不是强制字段：
- 如果用户明确给出了时间范围，尽量提取为结构化对象
- 如果用户没有明确给出时间范围，time_range 可以为 null
- 不要因为缺少 time_range 就直接要求用户补充，除非该任务明确必须依赖用户指定时间范围

6. 你可以参考以下典型执行模式，但不要机械套用：

- 如果用户要求“获取/同步/查看财务数据”，可只规划 DataAgent。
- 如果用户要求“分析财务表现/风险/指标变化”，通常需要 DataAgent + AnalysisAgent。
- 如果用户明确要求“生成报告/撰写结论/输出正式分析文档”，通常再加入 ReportAgent。
- 只有在需要质量审查、发现结果可能不完整、或用户明确要求复核时，才加入 ReflectionAgent。

原则：
1. 计划必须最小化，只包含完成当前任务所必要的步骤。
2. 不要因为存在某个 Agent 就默认把它加入计划。
3. 如果已有信息足够，就不要重复调用上游步骤。

7. 不要让 ReportAgent 在没有数据和分析结论的情况下直接产出最终报告
8. 不要让 AnalysisAgent 在没有数据准备的情况下先进行深度分析
9. ReflectionAgent 通常用于质量检查，而不是主执行入口
10. task_plan 应体现高层步骤，不要写得过细，不要出现底层实现细节

====================
【time_range 字段规则】
====================
1. time_range 必须是对象或 null，不能是自然语言字符串
2. 如果能识别用户给出的明确时间范围，则输出为：
{{
 "start_year": 整数,
 "start_month": 整数,
 "end_year": 整数,
 "end_month": 整数
}}
3. 如果用户没有明确给出时间范围，或者无法可靠提取，则直接设为 null
4. 不要为了凑字段而编造时间范围

====================
【task_plan 生成规则】
====================
1. task_plan 是一个数组，每个元素表示一个高层步骤
2. 每个步骤必须包含：
- step_id: int 类型，例如 1, 2, 3
- agent_name: 字符串，例如 "DataAgent"
- action: 字符串，表示该步骤动作
- description: 字符串，表示该步骤说明
3. step_id 应按执行顺序递增，例如 1, 2, 3
4. agent_name 必须使用系统中真实存在的 Agent 名称
5. 如果 needs_user_input = true，task_plan 可以为空，或者只保留非常高层说明

====================
【输出 JSON Schema】
====================
{{
"task_type": "financial_analysis | unknown",
"company_name": "字符串或 null",
"ts_code": "字符串或 null",
"time_range": {{
"start_year": 2023,
"start_month": 1,
"end_year": 2025,
"end_month": 12
}} 或 null,
"analysis_focus": "字符串或 null",
"output_mode": "report | summary",
"planner_message": "对规划结果的简短说明",
"task_plan": [
{{
  "step_id": 1,
  "agent": "DataAgent | AnalysisAgent | ReportAgent | ReflectionAgent",
  "action": "动作名",
  "description": "步骤描述"
}}
],
"needs_user_input": false,
"missing_fields": []
}}

====================
【缺失字段命名规范】
====================
只允许优先使用这些字段名：
- company_name
- ts_code
- company_name_or_ts_code
- time_range
- analysis_focus
- task_description

====================
【额外要求】
====================
1. 输出内容必须能被解析为合法 JSON
2. 可以使用 ```json ... ``` 代码块包裹
3. 不要输出与 JSON 无关的解释性文字
4. 不要添加上面 schema 之外的字段
5. 如果某个字段未知，可使用 null

====================
【用户输入】
====================
{user_query}
""".strip()
