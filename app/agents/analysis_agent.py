"""AnalysisAgent: minimal analysis implementation."""
import json

from app.skills.analysis.balance_sheet_evidence_tool import build_balance_sheet_evidence
from app.skills.analysis.cashflow_evidence_tool import build_cashflow_evidence
from app.skills.analysis.cross_statement_evidence_tool import build_cross_statement_evidence
from app.skills.analysis.fina_indicator_evidence_tool import build_fina_indicator_evidence
from app.skills.analysis.income_statement_evidence_tool import build_income_evidence
from app.skills.analysis.metric_groups import INCOME_GROUPS, BALANCE_SHEET_GROUPS, CASHFLOW_GROUPS, \
    FINA_INDICATOR_GROUPS, CROSS_STATEMENT_GROUPS
from app.skills.planning.planning_parser import parse_json_response


class AnalysisAgent:
    def __init__(
        self,
        llm_client,
        max_tool_rounds: int = 6
    ):
        self.llm_client = llm_client
        self.max_tool_rounds = max_tool_rounds

    def analyze(
        self,
        *,
        user_query: str,
        analysis_focus: str,
        company_profile: dict,
        time_range: dict,
        financial_data: dict,
        trans_message: str
    ) -> dict:
        tool_schema, tool_func_map = self._build_tools(financial_data)
        react_initial_messages = self._build_react_initial_messages(
            user_query=user_query,
            analysis_focus=analysis_focus,
            company_profile=company_profile,
            time_range=time_range,
            trans_message=trans_message,
            available_parts=list(financial_data.keys())
        )
        evidence = self._run_react_loop(messages=react_initial_messages, tool_schemas=tool_schema, tool_func_map=tool_func_map)
        evidence_json = json.dumps(evidence, ensure_ascii=False, default=str, indent=2)
        analysis_dict = self._finalize_analysis(
            user_query=user_query,
            analysis_focus=analysis_focus,
            company_profile=company_profile,
            time_range=time_range,
            evidence=evidence_json,
            trans_message=trans_message
        )
        return {
            "status": analysis_dict["status"],
            "summary": analysis_dict["summary"],
            "dimensions": analysis_dict["dimensions"],
            "data_limitations": analysis_dict["data_limitations"],
            "evidence": evidence_json,
            "conclusion": analysis_dict["conclusion"],
        }

    def _finalize_analysis(
            self,
            *,
            user_query: str,
            analysis_focus: str,
            company_profile: dict,
            time_range: dict,
            evidence: str,
            trans_message: str,
    ) -> dict:
        system_prompt, user_prompt = self._build_final_messages(
            user_query=user_query,
            analysis_focus=analysis_focus,
            company_profile=company_profile,
            time_range=time_range,
            evidence_json=evidence,
            trans_message=trans_message,
        )
        analysis_result = self.llm_client.generate(system_prompt, user_prompt)
        if not analysis_result:
            raise ValueError("LLM generate empty result.")
        return parse_json_response(analysis_result)


    def _build_tools(self, financial_data):
        # tools_schema
        tools_schema = []
        income_statement_tool_schema = {
            "type": "function",
            "function": {
                "name": "income_statement_evidence_tool",
                "description": (
                    "获取利润表证据，适合分析收入与利润规模、成本费用金额、研发与财务费用、"
                    "非主营损益、减值损失、归母利润和综合收益。不负责标准利润率、ROE、ROA 等比率。"
                ),
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "groups": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": list(INCOME_GROUPS.keys()),
                            },
                            "description": (
                                "利润表分组："
                                "profit_scale_layers=收入到净利润的金额层级；"
                                "cost_expense_amounts=营业成本与期间费用金额；"
                                "rd_and_finance_detail=研发投入、财务费用和利息拆解；"
                                "non_core_profit_sources=投资收益、公允价值变动等非主营损益；"
                                "impairment_losses=资产减值和信用减值损失；"
                                "profit_attribution=归母与少数股东损益分配；"
                                "comprehensive_income=其他综合收益与综合收益差异。"
                            ),
                        }
                    },
                    "required": ["groups"],
                    "additionalProperties": False,
                },
            },
        }
        balance_sheet_tool_schema = {
            "type": "function",
            "function": {
                "name": "balance_sheet_evidence_tool",
                "description": (
                    "获取资产负债表证据，适合分析资产结构、债务期限结构、应收存货占款、"
                    "应付和合同负债、商誉无形资产风险、在建工程和扩产压力。"
                ),
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "groups": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": list(BALANCE_SHEET_GROUPS.keys()),
                            },
                            "description": (
                                "资产负债表分组："
                                "asset_scale_structure=资产规模与流动/非流动资产结构；"
                                "debt_maturity_structure=有息债务期限结构与短债压力；"
                                "receivables_inventory=应收、合同资产、存货等经营占款；"
                                "payables_contract_liability=应付、预收与合同负债；"
                                "soft_asset_risk=商誉和无形资产风险；"
                                "construction_asset_risk=在建工程、扩产和未来转固压力。"
                            ),
                        }
                    },
                    "required": ["groups"],
                    "additionalProperties": False,
                },
            },
        }
        cashflow_statement_tool_schema = {
            "type": "function",
            "function": {
                "name": "cashflow_statement_evidence_tool",
                "description": (
                    "获取现金流量表证据，适合分析经营现金流入流出、经营现金流净额、"
                    "投资现金流和资本开支、筹资现金流、现金余额变化，以及间接法调节。"
                ),
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "groups": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": list(CASHFLOW_GROUPS.keys()),
                            },
                            "description": (
                                "现金流分组："
                                "operating_cash_inflows=经营现金流入结构和销售收现；"
                                "operating_cash_outflows=采购、人工、税费等经营现金流出；"
                                "operating_cash_net=经营活动最终沉淀的净现金流；"
                                "investing_capex_structure=投资现金流与资本开支压力；"
                                "financing_cashflow_structure=融资、偿债、分红付息结构；"
                                "cash_balance_change=现金及现金等价物变化；"
                                "indirect_operating_reconciliation=净利润调节为经营现金流的间接法解释。"
                            ),
                        }
                    },
                    "required": ["groups"],
                    "additionalProperties": False,
                },
            },
        }
        fina_indicator_tool_schema = {
            "type": "function",
            "function": {
                "name": "fina_indicator_evidence_tool",
                "description": (
                    "获取 TuShare fina_indicator 中已计算好的标准财务指标，适合分析每股价值、"
                    "利润率、费用率、回报率、周转效率、偿债能力、资本债务和基础利润质量。"
                ),
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "groups": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": list(FINA_INDICATOR_GROUPS.keys()),
                            },
                            "description": (
                                "财务指标分组："
                                "per_share_value=EPS、每股净资产、每股现金流等；"
                                "profitability_margin=毛利率、净利率、营业利润率等；"
                                "expense_cost_margin=成本率、费用率和减值占比；"
                                "return_efficiency=ROE、ROA、ROIC 等回报效率；"
                                "turnover_efficiency=存货、应收、资产周转效率；"
                                "liquidity_solvency=流动比率、速动比率、资产负债率等；"
                                "capital_cashflow_debt=EBITDA、自由现金流、带息债务、净债务等；"
                                "earnings_quality_basic=非经常性损益、扣非净利润和经营活动净收益。"
                            ),
                        }
                    },
                    "required": ["groups"],
                    "additionalProperties": False,
                },
            },
        }
        cross_statement_tool_schema = {
            "type": "function",
            "function": {
                "name": "cross_statement_evidence_tool",
                "description": (
                    "获取跨报表诊断证据，适合分析收入质量、利润质量、现金转化质量、"
                    "偿债压力、资本开支扩张压力和营运资本占款压力。用于判断财务质量和风险信号。"
                ),
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "groups": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": list(CROSS_STATEMENT_GROUPS.keys()),
                            },
                            "description": (
                                "跨表诊断分组："
                                "revenue_quality=收入、销售收现、应收存货匹配；"
                                "profit_quality=净利润、经营现金流、扣非利润和减值匹配；"
                                "cash_conversion_quality=利润和经营活动向自由现金流的转化；"
                                "debt_service_pressure=现金流和现金资源对债务压力的覆盖；"
                                "capex_expansion_pressure=资本开支、扩产和现金流压力；"
                                "working_capital_pressure=应收、存货、应付和营运资本占款压力。"
                            ),
                        }
                    },
                    "required": ["groups"],
                    "additionalProperties": False,
                },
            },
        }
        if financial_data.get("income_statements"):
            tools_schema.append(income_statement_tool_schema)
        if financial_data.get("balance_sheets"):
            tools_schema.append(balance_sheet_tool_schema)
        if financial_data.get("cashflow_statements"):
            tools_schema.append(cashflow_statement_tool_schema)
        if financial_data.get("financial_indicators"):
            tools_schema.append(fina_indicator_tool_schema)
        all_list = [
            "income_statements",
            "balance_sheets",
            "cashflow_statements",
            "financial_indicators",
        ]
        if all(item in list(financial_data.keys()) for item in all_list):
            tools_schema.append(cross_statement_tool_schema)

        # tool_func_map
        income_records = financial_data.get("income_statements", [])
        balance_records = financial_data.get("balance_sheets", [])
        cashflow_records = financial_data.get("cashflow_statements", [])
        fina_indicator_records = financial_data.get("financial_indicators", [])

        def bound_income_tool(*, groups: list[str]) -> dict:
            return build_income_evidence(
                records=income_records,
                metric_groups=groups,
            )

        def bound_balance_tool(*, groups: list[str]) -> dict:
            return build_balance_sheet_evidence(
                records=balance_records,
                metric_groups=groups,
            )

        def bound_cashflow_tool(*, groups: list[str]) -> dict:
            return build_cashflow_evidence(
                records=cashflow_records,
                metric_groups=groups,
            )

        def bound_fina_indicator_tool(*, groups: list[str]) -> dict:
            return build_fina_indicator_evidence(
                records=fina_indicator_records,
                metric_groups=groups,
            )

        def bound_cross_tool(*, groups: list[str]) -> dict:
            return build_cross_statement_evidence(
                income_records=income_records,
                balance_sheet_records=balance_records,
                cashflow_records=cashflow_records,
                fina_indicator_records=fina_indicator_records,
                metric_groups=groups,
            )

        tool_func_map = {
            "income_statement_evidence_tool": bound_income_tool,
            "balance_sheet_evidence_tool": bound_balance_tool,
            "cashflow_statement_evidence_tool": bound_cashflow_tool,
            "fina_indicator_evidence_tool": bound_fina_indicator_tool,
            "cross_statement_evidence_tool": bound_cross_tool,
        }

        return tools_schema, tool_func_map


    def _run_react_loop(
        self,
        *,
        messages: list[dict],
        tool_schemas: list[dict],
        tool_func_map: dict,
    ) -> list[dict]:
        evidence = []
        for round_index in range(self.max_tool_rounds):
            assistant_message = self.llm_client.generate(messages=messages, tools=tool_schemas)
            assistant_msg = {
                "role": "assistant",
                "content": assistant_message.content or "",
            }
            reasoning_content = getattr(assistant_message, "reasoning_content", None)
            if reasoning_content:
                assistant_msg["reasoning_content"] = reasoning_content
            tool_calls = getattr(assistant_message, "tool_calls", None) or []
            if tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tool_call.id,
                        "type": tool_call.type,
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments,
                        },
                    }
                    for tool_call in tool_calls
                ]
            messages.append(assistant_msg)

            # 没有 tool_calls，说明 ReAct loop 结束
            if not tool_calls:
                break

            # 有 tool_calls，执行所有工具
            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                raw_arguments = tool_call.function.arguments or "{}"

                arguments = parse_json_response(raw_arguments)
                if not arguments:
                    raise ValueError(f"tool arguments为空: {raw_arguments}")

                tool_result = self._execute_tool_call(
                    tool_name=tool_name,
                    arguments=arguments,
                    tool_func_map=tool_func_map,
                )

                evidence.append({
                    "round": round_index + 1,
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "result": tool_result,
                })

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result, ensure_ascii=False, default=str),
                })
        return evidence


    def _execute_tool_call(
            self,
            *,
            tool_name: str,
            arguments: dict,
            tool_func_map: dict,
    ) -> dict:
        tool_func = tool_func_map.get(tool_name)

        if tool_func is None:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}",
            }

        try:
            result = tool_func(**arguments)

            if not isinstance(result, dict):
                return {
                    "success": False,
                    "error": f"Tool {tool_name} returned non-dict result.",
                    "raw_result": str(result),
                }

            return result

        except Exception as e:
            return {
                "success": False,
                "error": f"Tool {tool_name} execution failed: {str(e)}",
            }


    def _build_react_initial_messages(
            self,
            *,
            user_query: str,
            analysis_focus: str,
            company_profile: dict,
            time_range: dict,
            trans_message: str,
            available_parts: list,
    ):
        time_str = f"{time_range.get("start_year")}年{time_range.get("start_month")}月~{time_range.get("end_year")}年{time_range.get("end_month")}月"
        system_prompt = """
你是一个专业的财务分析 AnalysisAgent，负责基于已经准备好的财务数据进行结构化财务分析。

你的核心任务不是直接生成最终报告，而是：
1. 理解用户问题和 analysis_focus；
2. 判断需要分析哪些财务维度；
3. 主动选择合适的财务指标工具和 group；
4. 基于工具返回的证据继续判断是否还需要更多工具；
5. 当证据足够时，停止调用工具，等待后续 final 阶段生成结构化 analysis_result。

你必须遵守以下原则：

【证据原则】
- 不能编造财务指标、财务数据或趋势判断。
- 涉及具体指标、金额、比率、趋势或风险判断时，应优先通过工具获取证据。
- 如果工具返回的数据不足、缺失或失败，不能强行得出确定结论，应在后续分析中体现数据限制。
- 不要因为工具可用就机械调用所有工具，应根据用户问题选择最相关的工具和 group。
- 一次可以调用一个或多个工具；如果多个维度都明显相关，可以并行请求多个 tool_calls。
- 如果已有证据足以回答当前问题，应停止调用工具，不要重复调用相近 group。

【任务边界】
- 你是 AnalysisAgent，不是 ReportAgent。当前阶段不需要生成完整自然语言报告。
- 你是财务分析 Agent，不是投资顾问。若用户问“股票能买吗”“是否值得投资”，只能从财务质量、盈利能力、现金流、偿债压力、成长质量等角度分析，不能直接给出买入、卖出或持有指令。
- 当前阶段只负责选择工具和收集证据；最终 JSON 输出由后续 final 阶段完成。
- 不要输出 Markdown 报告。
- 不要输出完整 analysis_result JSON。
- 如果需要证据，请直接调用工具；如果证据已经足够，请停止调用工具。
- 本轮只能调用 tools 参数中实际注册的工具；如果某类数据不在当前可用数据部分中，不要尝试调用对应工具。

【工具选择总则】
- income_statement_evidence_tool：用于利润表金额层面的证据，适合收入、利润、成本费用、研发费用、财务费用、非主营损益、减值损失、归母利润、综合收益等分析。
- balance_sheet_evidence_tool：用于资产负债表结构证据，适合资产结构、债务期限结构、应收存货占款、应付和合同负债、商誉无形资产、在建工程和扩产风险分析。
- cashflow_statement_evidence_tool：用于现金流量表过程证据，适合经营现金流入流出、经营现金流净额、投资现金流、筹资现金流、现金余额变化、间接法调节分析。
- fina_indicator_evidence_tool：用于 TuShare 已计算好的标准财务指标，适合利润率、费用率、ROE、ROA、ROIC、周转率、偿债指标、每股指标、扣非指标等快速分析。
- cross_statement_evidence_tool：用于跨报表诊断，适合收入质量、利润质量、现金转化质量、偿债压力、资本开支压力、营运资本压力等综合判断。

【常见问题与工具优先级】
- 如果用户问盈利能力、利润率、ROE、ROA：优先调用 fina_indicator_evidence_tool；如需解释金额变化，再调用 income_statement_evidence_tool。
- 如果用户问收入和利润规模变化：优先调用 income_statement_evidence_tool 的 profit_scale_layers。
- 如果用户问成本费用、研发投入、财务费用：优先调用 income_statement_evidence_tool 的 cost_expense_amounts 或 rd_and_finance_detail。
- 如果用户问利润质量、净利润是否可靠、扣非后盈利是否稳定：优先调用 fina_indicator_evidence_tool 的 earnings_quality_basic，并结合 cross_statement_evidence_tool 的 profit_quality。
- 如果用户问非主营损益、一次性收益、投资收益、公允价值变动：优先调用 income_statement_evidence_tool 的 non_core_profit_sources。
- 如果用户问现金流质量、经营现金流是否健康：优先调用 cashflow_statement_evidence_tool 的 operating_cash_net、operating_cash_inflows，并结合 cross_statement_evidence_tool 的 cash_conversion_quality 或 profit_quality。
- 如果用户问收入质量、收入增长是否扎实：优先调用 cross_statement_evidence_tool 的 revenue_quality；必要时结合 income_statement_evidence_tool 的 profit_scale_layers 和 balance_sheet_evidence_tool 的 receivables_inventory。
- 如果用户问偿债能力、债务压力：优先调用 fina_indicator_evidence_tool 的 liquidity_solvency 和 balance_sheet_evidence_tool 的 debt_maturity_structure；如需判断现金流覆盖债务，调用 cross_statement_evidence_tool 的 debt_service_pressure。
- 如果用户问资产质量：优先调用 balance_sheet_evidence_tool 的 receivables_inventory、soft_asset_risk、construction_asset_risk；如涉及减值对利润影响，结合 income_statement_evidence_tool 的 impairment_losses。
- 如果用户问扩产、资本开支、在建工程压力：优先调用 balance_sheet_evidence_tool 的 construction_asset_risk 和 cashflow_statement_evidence_tool 的 investing_capex_structure；如需综合判断扩张压力，调用 cross_statement_evidence_tool 的 capex_expansion_pressure。
- 如果用户问整体财务质量、有没有风险、股票能买吗：通常需要组合调用 fina_indicator_evidence_tool、cashflow_statement_evidence_tool 和 cross_statement_evidence_tool，必要时补充 income 或 balance_sheet 工具解释原因。

【group 选择指南】

income_statement_evidence_tool 可选 groups：
- profit_scale_layers：收入、营业利润、利润总额、净利润等金额层级。
- cost_expense_amounts：营业成本、营业总成本、销售费用、管理费用、税金及附加等金额。
- rd_and_finance_detail：研发费用、财务费用、利息费用、利息收入和净利息费用。
- non_core_profit_sources：投资收益、公允价值变动、其他收益、资产处置收益、营业外收支等非主营损益。
- impairment_losses：资产减值损失、信用减值损失及其对利润的拖累。
- profit_attribution：归母净利润、少数股东损益及利润归属结构。
- comprehensive_income：其他综合收益、归母综合收益与归母净利润差异。

balance_sheet_evidence_tool 可选 groups：
- asset_scale_structure：资产规模、流动资产、非流动资产、固定资产、货币资金结构。
- debt_maturity_structure：短期有息负债、长期有息负债、短债压力和现金覆盖短债情况。
- receivables_inventory：应收票据及应收账款、合同资产、存货等经营占款。
- payables_contract_liability：应付票据及应付账款、预收款项、合同负债和上下游占款能力。
- soft_asset_risk：商誉、无形资产及潜在减值风险。
- construction_asset_risk：在建工程、扩产周期、未来转固和资本开支压力。

cashflow_statement_evidence_tool 可选 groups：
- operating_cash_inflows：销售收现、经营现金流入结构和经营现金流入质量。
- operating_cash_outflows：采购、人工、税费等经营现金流出结构。
- operating_cash_net：经营活动现金流净额和经营现金流入转化能力。
- investing_capex_structure：投资现金流、资本开支、购建长期资产支付现金。
- financing_cashflow_structure：股权融资、债务融资、偿债、分红付息和筹资现金流。
- cash_balance_change：现金及现金等价物期初、期末和净增加额。
- indirect_operating_reconciliation：净利润调节为经营现金流的间接法解释，包括折旧摊销、存货、应收、应付变化。

fina_indicator_evidence_tool 可选 groups：
- per_share_value：EPS、扣非 EPS、每股净资产、每股经营现金流、每股自由现金流。
- profitability_margin：毛利率、净利率、营业利润率、EBIT 利润率等盈利指标。
- expense_cost_margin：销售成本率、期间费用率、销售费用率、管理费用率、财务费用率等。
- return_efficiency：ROE、扣非 ROE、ROA、总资产净利率、ROIC。
- turnover_efficiency：存货、应收账款、流动资产、固定资产、总资产周转率。
- liquidity_solvency：流动比率、速动比率、现金比率、资产负债率、权益乘数。
- capital_cashflow_debt：EBIT、EBITDA、FCFF、FCFE、带息债务、净债务、营运资金、投入资本。
- earnings_quality_basic：非经常性损益、扣非净利润、经营活动净收益等基础利润质量指标。

cross_statement_evidence_tool 可选 groups：
- revenue_quality：收入、销售收现、经营性应收、存货和合同资产之间的匹配。
- profit_quality：净利润、归母净利润、经营现金流、扣非净利润和减值损失之间的匹配。
- cash_conversion_quality：经营现金流、净利润、营业利润和资本开支之间的现金转化质量。
- debt_service_pressure：经营现金流、短期有息负债、净债务、偿债现金支出和分红付息压力。
- capex_expansion_pressure：资本开支、经营现金流、营业收入、折旧摊销和扩张压力。
- working_capital_pressure：净经营营运资本、收入、销售收现、应收存货和应付变化对现金流的影响。

【停止调用工具的条件】
当你已经获得足够证据覆盖用户问题的主要维度时，应停止调用工具。
如果工具返回失败、缺数据或无法支持某些分析，也可以停止调用工具，后续 final 阶段会在 data_limitations 中说明。
不要为了追求完整性而调用所有工具。
        """
        user_prompt = f"""
请基于以下任务信息进行财务分析证据收集。

【用户问题】
{user_query}

【分析重点 analysis_focus】
{analysis_focus}

【公司信息】
{company_profile}

【时间范围】
{time_str}

【Supervisor对于数据准备结果的反馈】
{trans_message}

【当前可用数据部分】
{available_parts}

请根据用户问题和 analysis_focus 判断需要调用哪些工具和 groups。
如果需要证据，请直接调用工具。
如果已经具备足够证据，请停止调用工具，等待后续 final 阶段生成结构化分析结果。
"""
        react_initial_messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ]
        return react_initial_messages

    def _build_final_messages(
            self,
            *,
            user_query: str,
            analysis_focus: str,
            company_profile: dict,
            time_range: dict,
            trans_message: str,
            evidence_json: str,
    ):
        time_str = f"{time_range.get("start_year")}年{time_range.get("start_month")}月~{time_range.get("end_year")}年{time_range.get("end_month")}月"

        system_prompt = """
你是多 Agent 财务分析系统中的 AnalysisAgent，当前处于 finalize 阶段。

你已经完成了 ReAct 工具调用阶段。现在你会收到：
1. 用户原始问题 user_query；
2. 分析重点 analysis_focus；
3. 公司信息 company_profile；
4. 时间范围 time_range；
5. Supervisor对于数据准备的审查反馈 trans_message；
6. ReAct 阶段已经筛选并调用工具得到的 evidence。

你的任务是：
基于 evidence 中的财务指标、工具结果和数据限制，生成最终结构化 analysis_result。

你必须遵守以下规则：

【阶段边界】
- 当前阶段不再调用工具。
- 当前阶段不再请求补充工具结果。
- 当前阶段不输出 ReAct 思考过程。
- 当前阶段只负责基于已有 evidence 进行归纳、判断和结构化输出。
- 不要输出解释性前缀。
- 最终只输出合法 JSON。

【证据使用规则】
- evidence 是 ReAct 阶段根据用户问题和 analysis_focus 筛选后的工具结果，应作为本次财务分析的唯一财务证据来源。
- 不能编造 evidence 中没有出现的财务指标、期间、金额、比率或趋势。
- 可以基于 evidence 中的多个指标做合理综合判断，但必须避免超出证据范围的强结论。
- 如果 evidence 不足以支撑某个维度的判断，应在 data_limitations 中说明。
- 如果某个工具失败、某些 group 没有返回数据、某些指标缺失，应在 data_limitations 中体现。
- supporting_metrics 只能从 evidence 中选择最关键的指标，不要虚构指标。
- 不要把所有 evidence 指标都堆进 supporting_metrics，只选择最能支撑该维度结论的指标。

【分析维度规则】
- dimensions 应根据 user_query、analysis_focus 和 evidence 动态决定。
- 不需要固定输出所有维度。
- 一般可选维度包括：盈利能力、成长能力、偿债能力、现金流质量、资产质量、经营质量。
- 如果用户只问单一维度，可以只输出 1 到 2 个 dimensions。
- 如果用户问整体财务质量、风险、股票能买吗、是否值得关注等综合问题，可以输出 3 到 6 个 dimensions。
- 每个 dimension 都必须有明确 conclusion、key_points 和 supporting_metrics。
- conclusion 要有详细的分析结论与步骤，必要时可在说明文字中穿插 evidence 中的指标来佐证。
- key_points 应直接解释该维度的主要判断，不要写空泛套话。

【status 规则】
- analysis_done：evidence 足以回答用户主要问题，且主要维度都有证据支撑。
- analysis_partial：可以回答部分问题，但部分维度存在数据缺失或证据不足。
- needs_more_data：当前 evidence 无法回答用户核心问题，需要 DataAgent 补充关键数据。
- analysis_failed：工具结果整体不可用，或者无法形成有效分析。

【投资类问题规则】
- 如果用户问“股票能买吗”“是否值得买”“能不能投资”等问题，不能直接给出买入、卖出、持有等投资指令。
- 应从财务质量、盈利能力、成长性、现金流、偿债压力、经营质量和风险因素角度分析。
- 必须在 conclusion 或 data_limitations 中说明：仅基于财务数据，不能替代完整投资决策，还需要结合估值、股价、行业周期、竞争格局和个人风险偏好。

【其他要求】
- supporting_metrics 如果数量很多，无需全部罗列，可以只挑选其中两三个输出。
- 最终的 conclusion 字段要有详细的、全局的完整结论与评估结果，字数不得少于200字。

【输出要求】
你必须只输出 JSON，字段如下：

{
  "status": "analysis_done | analysis_partial | needs_more_data | analysis_failed",
  "summary": "核心结论摘要",
  "dimensions": [
    {
      "name": "盈利能力 | 成长能力 | 偿债能力 | 现金流质量 | 资产质量 | 经营质量",
      "conclusion": "该维度的分析结论",
      "key_points": [
        "分析要点1",
        "分析要点2"
      ],
      "supporting_metrics": [
        {
          "name": "指标名称",
          "period": "YYYY-MM-DD",
          "value": 123.45,
          "unit": "元/%/倍/天/无"
        }
      ]
    }
  ],
  "data_limitations": [
    "数据限制说明"
  ],
  "conclusion": "面向用户问题的综合分析结论"
}

注意：
- 不要输出 evidence 字段。evidence 字段将由程序侧写回 analysis_result。
- JSON 中不要出现注释。     
"""
        user_prompt = f"""
请基于以下信息生成最终 analysis_result。

【用户问题 user_query】
{user_query}

【分析重点 analysis_focus】
{analysis_focus}

【公司信息 company_profile】
{company_profile}

【时间范围 time_range】
{time_str}

【Supervisor对于数据准备的审查反馈】
{trans_message}

【ReAct 阶段工具证据 evidence】
以下 evidence 是前一阶段根据用户问题筛选工具和 group 后得到的完整证据。请只基于这些 evidence 进行分析，不要编造额外财务数据。

{evidence_json}

请输出最终 analysis_result JSON。

要求：
1. 只输出 JSON。
2. 不要输出解释性文字。
3. dimensions 根据用户问题、analysis_focus 和 evidence 动态选择。
4. supporting_metrics 只能来自 evidence。
5. 如果 evidence 中缺少关键数据，请写入 data_limitations。
6. conclusion 必须直接回应用户问题。
"""
        return system_prompt, user_prompt

