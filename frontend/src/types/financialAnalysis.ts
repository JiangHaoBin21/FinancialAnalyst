export interface FinancialAnalysisRequest {
  query: string;
  thread_id?: string | null;
  include_state?: boolean;
}

export interface OverallScore {
  score?: number | string | null;
  label?: string | null;
  basis?: string | null;
  confidence?: "low" | "medium" | "high" | string | null;
}

export interface SupportingMetric {
  name?: string | null;
  period?: string | null;
  value?: number | string | null;
  unit?: string | null;
}

export interface AnalysisDimension {
  name?: string | null;
  conclusion?: string | null;
  key_points?: string[];
  supporting_metrics?: SupportingMetric[];
}

export interface AnalysisResult {
  status?: string | null;
  summary?: string | null;
  overall_score?: OverallScore | null;
  dimensions?: AnalysisDimension[];
  data_limitations?: string[];
  evidence?: string | null;
  conclusion?: string | null;
}

export interface OverallAssessment {
  score?: number | string | null;
  label?: string | null;
  basis?: string | null;
  confidence?: "low" | "medium" | "high" | string | null;
}

export interface ReportSection {
  heading?: string | null;
  summary?: string | null;
  key_points?: string[];
  supporting_metrics?: SupportingMetric[];
}

export interface ReportResult {
  status?: string | null;
  report_type?: string | null;
  title?: string | null;
  executive_summary?: string | null;
  overall_assessment?: OverallAssessment | null;
  sections?: ReportSection[];
  risk_warnings?: string[];
  data_limitations?: string[];
  conclusion?: string | null;
  disclaimer?: string | null;
  markdown_report?: string | null;
}

export interface ExecutionRecord {
  step?: string | null;
  agent?: string | null;
  success?: boolean;
  message?: string | null;
  metadata?: Record<string, unknown>;
}

export interface FinancialAnalysisResponse {
  thread_id: string;
  status?: string | null;
  current_stage?: string | null;
  next_step?: string | null;
  needs_user_input?: boolean;
  has_error?: boolean;
  assistant_message?: string | null;
  error_message?: string | null;
  final_report?: string | null;
  analysis_result?: AnalysisResult;
  report_result?: ReportResult;
  execution_history?: ExecutionRecord[];
}

export interface AnalysisFormPayload {
  company: string;
  year: string;
  question: string;
  focus: string;
  includeState: boolean;
}

export interface ApiErrorPayload {
  detail?: string;
}
