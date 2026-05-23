import re
from pathlib import Path
from datetime import datetime
from typing import Any


def sanitize_filename(filename: str, max_length: int = 80) -> str:
    """
    清理文件名，避免 Windows / Linux 不支持的特殊字符。
    """
    filename = filename.strip()

    # 替换非法字符
    filename = re.sub(r'[\\/:*?"<>|]', "_", filename)

    # 合并多个空白
    filename = re.sub(r"\s+", "_", filename)

    # 限制长度
    filename = filename[:max_length]

    return filename or "financial_report"


def save_markdown_report(
    report_result: dict[str, Any],
    output_dir: str | Path = "outputs/reports",
    filename_prefix: str | None = None,
) -> str | None:
    """
    将 ReportAgent 输出中的 markdown_report 保存为 .md 文件。

    返回：
        md 文件路径；如果 markdown_report 为空，则返回 None。
    """
    markdown_report = report_result.get("markdown_report")

    if not markdown_report:
        return None

    title = report_result.get("title") or "财务分析报告"
    safe_title = sanitize_filename(title)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if filename_prefix:
        safe_prefix = sanitize_filename(filename_prefix)
        filename = f"{safe_prefix}_{safe_title}_{timestamp}.md"
    else:
        filename = f"{safe_title}_{timestamp}.md"

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    file_path = output_path / filename

    file_path.write_text(markdown_report, encoding="utf-8")

    return str(file_path)