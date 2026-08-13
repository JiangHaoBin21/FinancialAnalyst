import axios, { AxiosError } from "axios";
import type {
  ApiErrorPayload,
  FinancialAnalysisRequest,
  FinancialAnalysisResponse,
} from "../types/financialAnalysis";

const configuredTimeout = Number(import.meta.env.VITE_API_TIMEOUT_MS ?? 0);
const apiTimeout = Number.isFinite(configuredTimeout) && configuredTimeout > 0 ? configuredTimeout : 0;

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || (import.meta.env.DEV ? "" : "http://127.0.0.1:8000"),
  timeout: apiTimeout,
  withCredentials: false,
  headers: { "Content-Type": "application/json" },
});

export async function createFinancialAnalysis(
  payload: FinancialAnalysisRequest,
): Promise<FinancialAnalysisResponse> {
  const response = await apiClient.post<FinancialAnalysisResponse>("/api/v1/financial-analysis", payload);
  return response.data;
}

export function getFriendlyApiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<ApiErrorPayload>;
    const detail = axiosError.response?.data?.detail;
    if (typeof detail === "string" && detail.trim()) return normalizeBackendError(detail);
    if (axiosError.code === "ECONNABORTED") {
      return "分析时间超过了页面等待上限，请稍后重试。";
    }
    if (!axiosError.response) {
      return "无法连接分析服务，请确认后端已经在 8000 端口启动。";
    }
  }
  return "分析任务暂时无法完成，请检查输入后稍后重试。";
}

function normalizeBackendError(message: string): string {
  if (message.includes("工作流执行失败")) {
    return "分析流程执行失败，请确认数据库、模型服务和 TuShare 配置正常。";
  }
  return message.length > 180 ? `${message.slice(0, 180)}...` : message;
}
