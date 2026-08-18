"""将结构化财务报告确定性渲染为 Markdown。"""

from __future__ import annotations

from typing import Any, Iterable


def render_markdown_report(report: dict[str, Any]) -> str:
    """根据标准 report_result 字段生成完整 Markdown 报告。"""
    title = _text(report.get("title"), "财务分析报告")
    executive_summary = _text(report.get("executive_summary"), "暂无核心摘要。")
    assessment = report.get("overall_assessment") or {}
    sections = report.get("sections") or []
    risk_warnings = report.get("risk_warnings") or []
    data_limitations = report.get("data_limitations") or []
    conclusion = _text(report.get("conclusion"), "暂无综合结论。")
    disclaimer = _text(
        report.get("disclaimer"),
        "本报告仅基于已获取的公开财务数据和模型分析结果生成，不构成任何投资建议。",
    )

    blocks = [
        f"# {title}",
        "## 一、核心结论\n\n" + executive_summary,
        "## 二、总体评价\n\n" + _render_assessment(assessment),
        "## 三、分维度分析\n\n" + _render_sections(sections),
        "## 四、风险提示\n\n" + _render_bullets(risk_warnings, "未识别到需要单独披露的风险提示。"),
        "## 五、数据限制\n\n" + _render_bullets(data_limitations, "当前分析未声明额外数据限制。"),
        "## 六、综合结论\n\n" + conclusion,
        "## 七、免责声明\n\n" + disclaimer,
    ]
    return "\n\n".join(block.strip() for block in blocks).strip() + "\n"


def _render_assessment(assessment: dict[str, Any]) -> str:
    score = assessment.get("score")
    score_text = "无法评分" if score is None or score == -1 else f"{score}/100"
    rows = [
        ("综合评分", score_text),
        ("评价标签", _text(assessment.get("label"), "未提供")),
        ("置信度", _text(assessment.get("confidence"), "medium")),
        ("评分依据", _text(assessment.get("basis"), "未提供")),
    ]
    lines = ["| 项目 | 内容 |", "| --- | --- |"]
    lines.extend(f"| {_escape_cell(name)} | {_escape_cell(value)} |" for name, value in rows)
    return "\n".join(lines)


def _render_sections(sections: Iterable[Any]) -> str:
    rendered: list[str] = []
    for index, raw_section in enumerate(sections, start=1):
        section = raw_section if isinstance(raw_section, dict) else {}
        heading = _text(section.get("heading"), f"维度 {index}")
        summary = _text(section.get("summary"), "暂无小结。")
        key_points = section.get("key_points") or []
        metrics = section.get("supporting_metrics") or []
        section_blocks = [f"### {index}. {heading}", summary]
        if key_points:
            section_blocks.append("#### 分析要点\n\n" + _render_bullets(key_points, ""))
        if metrics:
            section_blocks.append("#### 支撑指标\n\n" + _render_metrics(metrics))
        rendered.append("\n\n".join(section_blocks))
    return "\n\n".join(rendered) if rendered else "暂无可展示的分维度分析。"


def _render_metrics(metrics: Iterable[Any]) -> str:
    lines = [
        "| 指标 | 报告期 | 数值 | 单位 |",
        "| --- | --- | ---: | --- |",
    ]
    for raw_metric in metrics:
        metric = raw_metric if isinstance(raw_metric, dict) else {}
        lines.append(
            "| {name} | {period} | {value} | {unit} |".format(
                name=_escape_cell(_text(metric.get("name"), "未命名指标")),
                period=_escape_cell(_text(metric.get("period"), "--")),
                value=_escape_cell(_format_value(metric.get("value"))),
                unit=_escape_cell(_text(metric.get("unit"), "--")),
            )
        )
    return "\n".join(lines)


def _render_bullets(items: Iterable[Any], empty_text: str) -> str:
    values = [_text(item) for item in items if _text(item)]
    if not values:
        return empty_text
    return "\n".join(f"- {value}" for value in values)


def _format_value(value: Any) -> str:
    if value is None:
        return "--"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def _escape_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def _text(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text or default
