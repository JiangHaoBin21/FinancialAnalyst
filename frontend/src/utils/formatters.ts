import type {
  FinancialAnalysisResponse,
  OverallAssessment,
  OverallScore,
  SupportingMetric,
} from "../types/financialAnalysis";

export function compactText(value: unknown, fallback = "暂无数据"): string {
  if (typeof value === "string" && value.trim()) {
    return value.trim();
  }

  if (typeof value === "number") {
    return String(value);
  }

  return fallback;
}

export function formatScore(score: OverallScore | OverallAssessment | null | undefined): string {
  const raw = score?.score;
  if (raw === null || raw === undefined || raw === "") {
    return "--";
  }

  const numeric = typeof raw === "number" ? raw : Number(raw);
  if (Number.isFinite(numeric)) {
    return numeric < 0 ? "--" : numeric.toFixed(numeric % 1 === 0 ? 0 : 1);
  }

  return String(raw);
}

export function formatMetricValue(metric: SupportingMetric): string {
  const value = metric.value === null || metric.value === undefined ? "--" : metric.value;
  const unit = metric.unit ? ` ${metric.unit}` : "";
  return `${value}${unit}`;
}

export function getOverallScore(response: FinancialAnalysisResponse | null): OverallScore | OverallAssessment | null {
  return (
    response?.report_result?.overall_assessment ||
    response?.analysis_result?.overall_score ||
    null
  );
}

export function getSummary(response: FinancialAnalysisResponse | null): string {
  return compactText(
    response?.report_result?.executive_summary ||
      response?.analysis_result?.summary ||
      response?.assistant_message,
    "等待提交分析任务后生成摘要。",
  );
}

export function getReportMarkdown(response: FinancialAnalysisResponse | null): string {
  return compactText(
    response?.final_report || response?.report_result?.markdown_report,
    "",
  );
}

export function collectMetrics(response: FinancialAnalysisResponse | null): SupportingMetric[] {
  const fromReport =
    response?.report_result?.sections?.flatMap((section) => section.supporting_metrics || []) ||
    [];
  const fromAnalysis =
    response?.analysis_result?.dimensions?.flatMap(
      (dimension) => dimension.supporting_metrics || [],
    ) || [];
  const merged = [...fromReport, ...fromAnalysis].filter((metric) => metric.name);
  const unique = new Map<string, SupportingMetric>();

  for (const metric of merged) {
    const key = `${metric.name}-${metric.period}-${metric.value}`;
    if (!unique.has(key)) {
      unique.set(key, metric);
    }
  }

  return Array.from(unique.values()).slice(0, 6);
}
