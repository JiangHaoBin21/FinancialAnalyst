from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.skills.analysis.metric_groups import INCOME_METRIC_GROUPS
from app.skills.analysis.metric_registry import INCOME_METRIC_REGISTRY


# ============================================================
# 3. IncomeMetricTool
# ============================================================

class IncomeMetricTool:
    """
    利润表派生指标计算工具。

    边界：
    - 不查数据库
    - 不调用 TuShare
    - 不落库
    - 不判断趋势
    - 不生成风险标签
    - 只从 Data 阶段已准备好的 income_records 中计算数字证据
    """

    tool_name = "income_metric_tool"
    source_statement = "income"
    source_table = "fact_income"

    def run(
        self,
        income_records: list[dict[str, Any]],
        ts_code: str,
        output_start_date: str | date,
        output_end_date: str | date,
        metric_groups: list[str],
        frequency: str = "annual",
        metric_version: str = "v1",
    ) -> dict[str, Any]:
        """
        Args:
            income_records:
                Data 阶段已经准备好的利润表数据。
                建议每条记录是 dict，并且至少包含 end_date 字段。

            ts_code:
                股票代码，例如 300750.SZ。

            output_start_date / output_end_date:
                用户真正要分析的输出范围。
                注意：income_records 里可以包含更早的数据，比如为了计算同比多准备的上一年数据。

            metric_groups:
                大模型选择的指标组，例如：
                ["income_growth", "profit_growth", "growth_spread"]

            frequency:
                annual / quarterly / ttm 等。V1 可先用 annual。

            metric_version:
                指标口径版本。
        """

        output_start = self._to_date(output_start_date)
        output_end = self._to_date(output_end_date)

        # output_metric_codes：用户/大模型请求的指标，最终返回给大模型
        # compute_metric_codes：实际计算所需指标，会自动补齐 depends_on 依赖，但不一定返回给大模型
        output_metric_codes, compute_metric_codes = self._resolve_metric_codes(metric_groups)
        output_metric_code_set = set(output_metric_codes)

        all_records = self._sort_records(income_records)

        # 用全部数据建立：报告期 -> record 的映射。
        # 这样即使 2021 不在输出范围内，也能用于计算 2022 的同比。
        records_by_date = self._build_record_map_by_end_date(all_records)

        # 只对用户真正关心的时间范围输出指标。
        output_records = self._filter_output_records(
            all_records,
            output_start,
            output_end,
            frequency=frequency,
        )

        results: list[dict[str, Any]] = []
        missing_requirements: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        # 先处理非 CAGR 指标。CAGR 是整个区间指标，后面单独处理。
        non_cagr_metric_codes = [
            code for code in compute_metric_codes
            if INCOME_METRIC_REGISTRY[code]["metric_type"] != "cagr"
        ]
        cagr_metric_codes = [
            code for code in compute_metric_codes
            if INCOME_METRIC_REGISTRY[code]["metric_type"] == "cagr"
        ]

        for cur_record in output_records:
            cur_date = self._get_record_end_date(cur_record)
            cur_date_key = cur_date.isoformat()

            base_date = self._previous_year_same_period(cur_date)
            base_date_key = base_date.isoformat()
            base_record = records_by_date.get(base_date_key)

            computed_for_period: dict[str, Any] = {}

            # 第一轮：计算 single_period / composition_ratio / yoy / yoy_change
            for metric_code in non_cagr_metric_codes:
                metric_def = INCOME_METRIC_REGISTRY[metric_code]
                metric_type = metric_def["metric_type"]

                if metric_type == "growth_spread":
                    continue

                if metric_type in {"yoy", "yoy_change"} and base_record is None:
                    # 依赖补算指标如果缺基期，不直接暴露给大模型；
                    # 只有用户真正请求的指标缺失时，才返回 missing。
                    if metric_code in output_metric_code_set:
                        missing_requirements.append({
                            "name": metric_def.get("name", metric_code),
                            "period": cur_date_key,
                            "missing": base_date_key,
                            "reason": "missing_base_period",
                        })
                    continue

                try:
                    metric_result = self._calculate_metric(
                        ts_code=ts_code,
                        metric_code=metric_code,
                        metric_def=metric_def,
                        cur_record=cur_record,
                        base_record=base_record,
                        frequency=frequency,
                        metric_version=metric_version,
                    )

                    if metric_result is not None:
                        results.append(metric_result)
                        computed_for_period[metric_code] = metric_result["value"]

                except Exception as exc:
                    errors.append({
                        "metric_code": metric_code,
                        "end_date": cur_date_key,
                        "error": str(exc),
                    })

            # 第二轮：计算依赖同比指标的 growth_spread
            for metric_code in non_cagr_metric_codes:
                metric_def = INCOME_METRIC_REGISTRY[metric_code]

                if metric_def["metric_type"] != "growth_spread":
                    continue

                depends_on = metric_def["depends_on"]
                missing_inputs = [
                    dep for dep in depends_on
                    if dep not in computed_for_period
                ]

                if missing_inputs:
                    if metric_code in output_metric_code_set:
                        missing_requirements.append({
                            "name": metric_def.get("name", metric_code),
                            "period": cur_date_key,
                            "missing": [
                                INCOME_METRIC_REGISTRY.get(dep, {}).get("name", dep)
                                for dep in missing_inputs
                            ],
                            "reason": "missing_dependent_metric",
                        })
                    continue

                try:
                    metric_result = self._calculate_growth_spread(
                        ts_code=ts_code,
                        metric_code=metric_code,
                        metric_def=metric_def,
                        cur_record=cur_record,
                        computed_for_period=computed_for_period,
                        frequency=frequency,
                        metric_version=metric_version,
                    )

                    if metric_result is not None:
                        results.append(metric_result)
                        computed_for_period[metric_code] = metric_result["value"]

                except Exception as exc:
                    errors.append({
                        "metric_code": metric_code,
                        "end_date": cur_date_key,
                        "error": str(exc),
                    })

        # CAGR 是区间指标，只计算一次：output_start_date -> output_end_date
        for metric_code in cagr_metric_codes:
            metric_def = INCOME_METRIC_REGISTRY[metric_code]

            start_record = records_by_date.get(output_start.isoformat())
            end_record = records_by_date.get(output_end.isoformat())

            if start_record is None:
                if metric_code in output_metric_code_set:
                    missing_requirements.append({
                        "name": metric_def.get("name", metric_code),
                        "period": self._format_period(output_start, output_end),
                        "missing": output_start.isoformat(),
                        "reason": "missing_cagr_start_period",
                    })
                continue

            if end_record is None:
                if metric_code in output_metric_code_set:
                    missing_requirements.append({
                        "name": metric_def.get("name", metric_code),
                        "period": self._format_period(output_start, output_end),
                        "missing": output_end.isoformat(),
                        "reason": "missing_cagr_end_period",
                    })
                continue

            try:
                value = self._calculate_cagr(metric_def, start_record, end_record)

                if value is None:
                    if metric_code in output_metric_code_set:
                        missing_requirements.append({
                            "name": metric_def.get("name", metric_code),
                            "period": self._format_period(output_start, output_end),
                            "reason": "invalid_cagr_inputs",
                        })
                    continue

                result = self._build_metric_result(
                    ts_code=ts_code,
                    metric_code=metric_code,
                    metric_def=metric_def,
                    start_date=output_start,
                    end_date=output_end,
                    value=value,
                    frequency=frequency,
                    metric_version=metric_version,
                    extra_source_fields={
                        "start_period": output_start.isoformat(),
                        "end_period": output_end.isoformat(),
                        "years": self._years_between(output_start, output_end),
                    },
                )
                results.append(result)

            except Exception as exc:
                errors.append({
                    "metric_code": metric_code,
                    "start_date": output_start.isoformat(),
                    "end_date": output_end.isoformat(),
                    "error": str(exc),
                })

        return {
            "tool": self.tool_name,
            "groups": metric_groups,
            "range": f"{output_start.isoformat()}~{output_end.isoformat()}",
            # 返回给大模型的是聚合压缩后的指标，不暴露 metric_code 和内部依赖指标。
            "metrics": self._format_metrics_for_llm(results, output_metric_codes),
            "missing": missing_requirements,
            "errors": errors,
        }

    # ========================================================
    # metric code / group
    # ========================================================

    def _resolve_metric_codes(self, metric_groups: list[str]) -> tuple[list[str], list[str]]:
        """
        将大模型选择的 metric_groups 展开成两组指标：
        1. output_metric_codes：用户/大模型真正请求的指标，最终返回给 LLM。
        2. compute_metric_codes：实际计算所需指标，会自动补齐 depends_on 依赖。

        例如：
        growth_spread 中的 oper_cost_yoy_minus_revenue_yoy 依赖 oper_cost_yoy 和 revenue_yoy。
        即使大模型没有显式选择 cost_expense_change，也会自动补算 oper_cost_yoy，避免出现假 missing。
        """
        if not metric_groups:
            raise ValueError("metric_groups must not be empty")

        output_metric_codes: list[str] = []
        compute_metric_codes: list[str] = []
        seen_output: set[str] = set()
        seen_compute: set[str] = set()

        def add_compute_metric(metric_code: str) -> None:
            if metric_code not in INCOME_METRIC_REGISTRY:
                raise ValueError(f"Metric code not found in registry: {metric_code}")

            if metric_code in seen_compute:
                return

            # 先补齐依赖，再加入当前指标，保证计算顺序稳定。
            metric_def = INCOME_METRIC_REGISTRY[metric_code]
            for dep in metric_def.get("depends_on", []):
                add_compute_metric(dep)

            compute_metric_codes.append(metric_code)
            seen_compute.add(metric_code)

        for group in metric_groups:
            if group not in INCOME_METRIC_GROUPS:
                raise ValueError(f"Unsupported income metric group: {group}")

            for metric_code in INCOME_METRIC_GROUPS[group]:
                if metric_code not in INCOME_METRIC_REGISTRY:
                    raise ValueError(f"Metric code not found in registry: {metric_code}")

                if metric_code not in seen_output:
                    output_metric_codes.append(metric_code)
                    seen_output.add(metric_code)

                add_compute_metric(metric_code)

        return output_metric_codes, compute_metric_codes

    # ========================================================
    # main calculation dispatch
    # ========================================================

    def _calculate_metric(
        self,
        ts_code: str,
        metric_code: str,
        metric_def: dict[str, Any],
        cur_record: dict[str, Any],
        base_record: dict[str, Any] | None,
        frequency: str,
        metric_version: str,
    ) -> dict[str, Any] | None:
        metric_type = metric_def["metric_type"]
        cur_date = self._get_record_end_date(cur_record)

        if metric_type == "single_period":
            value = self._calculate_single_period(metric_def, cur_record)
            start_date = cur_date
            end_date = cur_date

        elif metric_type == "composition_ratio":
            value = self._calculate_composition_ratio(metric_def, cur_record)
            start_date = cur_date
            end_date = cur_date

        elif metric_type == "yoy":
            if base_record is None:
                return None

            value = self._calculate_yoy(metric_def, cur_record, base_record)
            start_date = self._get_record_end_date(base_record)
            end_date = cur_date

        elif metric_type == "yoy_change":
            if base_record is None:
                return None

            value = self._calculate_yoy_change(metric_def, cur_record, base_record)
            start_date = self._get_record_end_date(base_record)
            end_date = cur_date

        else:
            raise ValueError(f"Unsupported metric_type in _calculate_metric: {metric_type}")

        if value is None:
            return None

        return self._build_metric_result(
            ts_code=ts_code,
            metric_code=metric_code,
            metric_def=metric_def,
            start_date=start_date,
            end_date=end_date,
            value=value,
            frequency=frequency,
            metric_version=metric_version,
        )

    def _calculate_single_period(
        self,
        metric_def: dict[str, Any],
        record: dict[str, Any],
    ) -> Decimal | None:
        operation = metric_def["operation"]

        if operation == "subtract":
            left = self._get_decimal(record, metric_def["left"])
            right = self._get_decimal(record, metric_def["right"])

            if left is None or right is None:
                return None

            return left - right

        if operation == "sum":
            values = [
                self._get_decimal(record, field)
                for field in metric_def["fields"]
            ]

            if any(v is None for v in values):
                return None

            return sum(values, Decimal("0"))

        raise ValueError(f"Unsupported single_period operation: {operation}")

    def _calculate_composition_ratio(
        self,
        metric_def: dict[str, Any],
        record: dict[str, Any],
    ) -> Decimal | None:
        operation = metric_def["operation"]

        if operation == "divide":
            numerator = self._get_decimal(record, metric_def["numerator"])
            denominator = self._get_decimal(record, metric_def["denominator"])
            return self._safe_divide(numerator, denominator)

        if operation == "divide_derived":
            numerator = self._calculate_derived_value(
                record,
                metric_def["numerator_derived"],
            )
            denominator = self._calculate_derived_value(
                record,
                metric_def["denominator_derived"],
            )
            return self._safe_divide(numerator, denominator)

        raise ValueError(f"Unsupported composition_ratio operation: {operation}")

    def _calculate_yoy(
        self,
        metric_def: dict[str, Any],
        cur_record: dict[str, Any],
        base_record: dict[str, Any],
    ) -> Decimal | None:
        cur_value, base_value = self._get_current_and_base_values(
            metric_def,
            cur_record,
            base_record,
        )

        if cur_value is None or base_value is None:
            return None

        return self._safe_divide(cur_value - base_value, base_value)

    def _calculate_yoy_change(
        self,
        metric_def: dict[str, Any],
        cur_record: dict[str, Any],
        base_record: dict[str, Any],
    ) -> Decimal | None:
        cur_value, base_value = self._get_current_and_base_values(
            metric_def,
            cur_record,
            base_record,
        )

        if cur_value is None or base_value is None:
            return None

        return cur_value - base_value

    def _calculate_growth_spread(
        self,
        ts_code: str,
        metric_code: str,
        metric_def: dict[str, Any],
        cur_record: dict[str, Any],
        computed_for_period: dict[str, Any],
        frequency: str,
        metric_version: str,
    ) -> dict[str, Any] | None:
        left_metric, right_metric = metric_def["depends_on"]

        left_value = self._to_decimal(computed_for_period.get(left_metric))
        right_value = self._to_decimal(computed_for_period.get(right_metric))

        if left_value is None or right_value is None:
            return None

        value = left_value - right_value

        cur_date = self._get_record_end_date(cur_record)
        base_date = self._previous_year_same_period(cur_date)

        return self._build_metric_result(
            ts_code=ts_code,
            metric_code=metric_code,
            metric_def=metric_def,
            start_date=base_date,
            end_date=cur_date,
            value=value,
            frequency=frequency,
            metric_version=metric_version,
            extra_source_fields={
                "derived_inputs": metric_def["depends_on"],
                "base_period": base_date.isoformat(),
                "current_period": cur_date.isoformat(),
            },
        )

    def _calculate_cagr(
        self,
        metric_def: dict[str, Any],
        start_record: dict[str, Any],
        end_record: dict[str, Any],
    ) -> Decimal | None:
        field = metric_def["field"]

        start_value = self._get_decimal(start_record, field)
        end_value = self._get_decimal(end_record, field)

        if start_value is None or end_value is None:
            return None

        # CAGR 对非正数不友好，V1 直接不计算。
        if start_value <= 0 or end_value <= 0:
            return None

        start_date = self._get_record_end_date(start_record)
        end_date = self._get_record_end_date(end_record)
        years = self._years_between(start_date, end_date)

        if years <= 0:
            return None

        # Decimal 不适合直接做小数幂，这里转 float 后再转回 Decimal。
        value = (float(end_value) / float(start_value)) ** (1 / years) - 1
        return Decimal(str(value))

    # ========================================================
    # derived values
    # ========================================================

    def _get_current_and_base_values(
        self,
        metric_def: dict[str, Any],
        cur_record: dict[str, Any],
        base_record: dict[str, Any],
    ) -> tuple[Decimal | None, Decimal | None]:
        if "field" in metric_def:
            field = metric_def["field"]
            return (
                self._get_decimal(cur_record, field),
                self._get_decimal(base_record, field),
            )

        if metric_def.get("derived_field") == "period_expense":
            return (
                self._calculate_period_expense(cur_record),
                self._calculate_period_expense(base_record),
            )

        raise ValueError("metric_def must define field or derived_field")

    def _calculate_derived_value(
        self,
        record: dict[str, Any],
        derived_name: str,
    ) -> Decimal | None:
        if derived_name == "period_expense":
            return self._calculate_period_expense(record)

        if derived_name == "gross_profit":
            revenue = self._get_decimal(record, "revenue")
            oper_cost = self._get_decimal(record, "oper_cost")

            if revenue is None or oper_cost is None:
                return None

            return revenue - oper_cost

        raise ValueError(f"Unsupported derived value: {derived_name}")

    def _calculate_period_expense(
        self,
        record: dict[str, Any],
    ) -> Decimal | None:
        sell_exp = self._get_decimal(record, "sell_exp")
        admin_exp = self._get_decimal(record, "admin_exp")
        fin_exp = self._get_decimal(record, "fin_exp")

        if sell_exp is None or admin_exp is None or fin_exp is None:
            return None

        return sell_exp + admin_exp + fin_exp

    # ========================================================
    # records helpers
    # ========================================================

    def _sort_records(
        self,
        records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return sorted(records, key=lambda r: self._get_record_end_date(r))

    def _build_record_map_by_end_date(
        self,
        records: list[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}

        for record in records:
            end_date = self._get_record_end_date(record)
            key = end_date.isoformat()

            if key in result:
                raise ValueError(
                    f"Duplicate income record for end_date={key}. "
                    "Please ensure Data stage normalizes records to one record per period."
                )

            result[key] = record

        return result

    def _filter_output_records(
            self,
            records: list[dict[str, Any]],
            output_start_date: date,
            output_end_date: date,
            frequency: str,
    ) -> list[dict[str, Any]]:
        filtered = []

        for record in records:
            end_date = self._get_record_end_date(record)

            if not (output_start_date <= end_date <= output_end_date):
                continue

            if not self._match_frequency(end_date, frequency):
                continue

            filtered.append(record)

        return filtered

    def _match_frequency(self, end_date: date, frequency: str) -> bool:
        month_day = (end_date.month, end_date.day)

        if frequency == "annual":
            return month_day == (12, 31)

        if frequency == "quarterly":
            return month_day in {
                (3, 31),
                (6, 30),
                (9, 30),
                (12, 31),
            }

        if frequency == "semiannual":
            return month_day in {
                (6, 30),
                (12, 31),
            }

        # 默认不额外过滤
        if frequency == "all":
            return True

        raise ValueError(f"Unsupported frequency: {frequency}")

    def _get_record_end_date(self, record: dict[str, Any]) -> date:
        raw = self._get_raw_value(record, "end_date")

        if raw is None:
            raise ValueError("income record missing required field: end_date")

        return self._to_date(raw)

    # ========================================================
    # result builder
    # ========================================================

    def _build_metric_result(
        self,
        ts_code: str,
        metric_code: str,
        metric_def: dict[str, Any],
        start_date: date,
        end_date: date,
        value: Decimal,
        frequency: str,
        metric_version: str,
        extra_source_fields: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        内部计算结果。
        注意：这里保留 _code 只是为了后续过滤和聚合；最终返回给 LLM 时会移除。
        """
        unit = metric_def["unit"]
        rounded_value = self._round_value(value, digits=4)

        return {
            "_code": metric_code,
            "name": metric_def.get("name", metric_code),
            "period": self._format_period(start_date, end_date),
            "value": rounded_value,
            "unit": unit,
            "display": self._format_metric_display_value(rounded_value, unit),
        }

    def _format_metrics_for_llm(
        self,
        metric_results: list[dict[str, Any]],
        output_metric_codes: list[str],
    ) -> list[dict[str, Any]]:
        """
        将逐条指标压缩为按指标聚合的 LLM 友好格式。

        输入内部结果：
        [
          {"_code": "revenue_yoy", "name": "营业收入同比增长率", "period": "2022", "display": "25.00%"},
          {"_code": "revenue_yoy", "name": "营业收入同比增长率", "period": "2023", "display": "20.00%"},
        ]

        输出给大模型：
        [
          {
            "name": "营业收入同比增长率",
            "unit": "ratio",
            "values": {
              "2022": "25.00%",
              "2023": "20.00%"
            }
          }
        ]
        """
        output_set = set(output_metric_codes)
        grouped: dict[str, dict[str, Any]] = {}

        for item in metric_results:
            metric_code = item.get("_code")
            if metric_code not in output_set:
                continue

            if metric_code not in grouped:
                grouped[metric_code] = {
                    "name": item["name"],
                    "unit": item["unit"],
                    "values": {},
                }

            grouped[metric_code]["values"][item["period"]] = item["display"]

        # 按 output_metric_codes 的顺序输出，便于结果稳定。
        return [
            grouped[metric_code]
            for metric_code in output_metric_codes
            if metric_code in grouped
        ]

    def _format_period(self, start_date: date, end_date: date) -> str:
        if start_date == end_date:
            return end_date.isoformat()

        return f"{start_date.isoformat()}~{end_date.isoformat()}"

    def _round_value(self, value: Decimal, digits: int = 4) -> float:
        quant = Decimal("1").scaleb(-digits)
        return float(value.quantize(quant))

    def _format_metric_display_value(self, value: float, unit: str) -> str:
        if unit == "ratio":
            return f"{value * 100:.2f}%"

        return str(value)


    # ========================================================
    # date / decimal helpers
    # ========================================================

    def _previous_year_same_period(self, current_date: date) -> date:
        try:
            return current_date.replace(year=current_date.year - 1)
        except ValueError:
            # 处理 2月29日 这种闰年日期，财报 end_date 一般不会遇到。
            return current_date.replace(year=current_date.year - 1, day=28)

    def _years_between(self, start_date: date, end_date: date) -> float:
        return (end_date - start_date).days / 365.25

    def _to_date(self, value: str | date | datetime) -> date:
        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        if isinstance(value, str):
            return datetime.strptime(value, "%Y-%m-%d").date()

        raise TypeError(f"Unsupported date value: {value!r}")

    def _get_raw_value(
        self,
        record: dict[str, Any],
        field_name: str,
    ) -> Any:
        # 当前建议 Data 阶段传 dict。
        # 这里顺手兼容 ORM 对象，方便你调试。
        if isinstance(record, dict):
            return record.get(field_name)

        return getattr(record, field_name, None)

    def _get_decimal(
        self,
        record: dict[str, Any],
        field_name: str,
    ) -> Decimal | None:
        value = self._get_raw_value(record, field_name)
        return self._to_decimal(value)

    def _to_decimal(self, value: Any) -> Decimal | None:
        if value is None:
            return None

        if isinstance(value, Decimal):
            return value

        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return None

    def _safe_divide(
        self,
        numerator: Decimal | None,
        denominator: Decimal | None,
    ) -> Decimal | None:
        if numerator is None or denominator is None:
            return None

        if denominator == 0:
            return None

        return numerator / denominator


# ============================================================
# 4. 简单测试示例
# ============================================================

if __name__ == "__main__":
    income_records = [
        {
            "end_date": "2021-12-31",
            "revenue": 80,
            "total_revenue": 82,
            "oper_cost": 50,
            "total_cogs": 60,
            "sell_exp": 3,
            "admin_exp": 4,
            "fin_exp": 1,
            "operate_profit": 12,
            "total_profit": 11,
            "income_tax": 2,
            "net_profit": 9,
            "n_income_attr_p": 8,
            "minority_gain": 1,
            "basic_eps": 1.0,
            "diluted_eps": 0.95,
            "invest_income": 0.5,
            "assets_impair_loss": 0.2,
            "compr_inc_attr_p": 8.2,
        },
        {
            "end_date": "2022-12-31",
            "revenue": 100,
            "total_revenue": 103,
            "oper_cost": 60,
            "total_cogs": 72,
            "sell_exp": 4,
            "admin_exp": 5,
            "fin_exp": 1,
            "operate_profit": 15,
            "total_profit": 14,
            "income_tax": 3,
            "net_profit": 11,
            "n_income_attr_p": 10,
            "minority_gain": 1,
            "basic_eps": 1.2,
            "diluted_eps": 1.15,
            "invest_income": 0.8,
            "assets_impair_loss": 0.3,
            "compr_inc_attr_p": 10.3,
        },
        {
            "end_date": "2023-12-31",
            "revenue": 120,
            "total_revenue": 125,
            "oper_cost": 78,
            "total_cogs": 92,
            "sell_exp": 5,
            "admin_exp": 6,
            "fin_exp": 2,
            "operate_profit": 16,
            "total_profit": 15,
            "income_tax": 3,
            "net_profit": 12,
            "n_income_attr_p": 11,
            "minority_gain": 1,
            "basic_eps": 1.3,
            "diluted_eps": 1.25,
            "invest_income": 1.0,
            "assets_impair_loss": 0.4,
            "compr_inc_attr_p": 11.2,
        },
    ]

    tool = IncomeMetricTool()

    result = tool.run(
        income_records=income_records,
        ts_code="300750.SZ",
        output_start_date="2022-12-31",
        output_end_date="2023-12-31",
        metric_groups=[
            "income_growth",
            "profit_growth",
            "growth_spread",
            "profit_structure",
        ],
        frequency="annual",
    )

    from pprint import pprint
    pprint(result)