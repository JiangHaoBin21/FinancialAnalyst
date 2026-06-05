import axios, { AxiosError } from "axios";
import type {
  ApiErrorPayload,
  FinancialAnalysisRequest,
  FinancialAnalysisResponse,
} from "../types/financialAnalysis";

const configuredTimeout = Number(import.meta.env.VITE_API_TIMEOUT_MS ?? 0);
const apiTimeout =
  Number.isFinite(configuredTimeout) && configuredTimeout > 0
    ? configuredTimeout
    : 0;

const apiClient = axios.create({
  baseURL:
    import.meta.env.VITE_API_BASE_URL ||
    (import.meta.env.DEV ? "" : "http://127.0.0.1:8000"),
  timeout: apiTimeout,
  withCredentials: false,
  headers: {
    "Content-Type": "application/json",
  },
});

export async function createFinancialAnalysis(
  payload: FinancialAnalysisRequest,
): Promise<FinancialAnalysisResponse> {
  const response = await apiClient.post<FinancialAnalysisResponse>(
    "/api/v1/financial-analysis",
    payload,
  );
  return response.data;
}

export function getFriendlyApiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<ApiErrorPayload>;
    const detail = axiosError.response?.data?.detail;

    if (typeof detail === "string" && detail.trim()) {
      return normalizeBackendError(detail);
    }

    if (axiosError.code === "ECONNABORTED") {
      return "分析耗时超过前端等待时间。当前后端接口是同步执行模式，如果希望等待完整报告，请将 VITE_API_TIMEOUT_MS 设为 0 或更大的毫秒数后重启前端。";
    }

    if (!axiosError.response) {
      return "浏览器未收到后端响应。请确认 FastAPI 正在 8000 端口运行；开发环境会通过 Vite 代理转发 /api 请求。";
    }
  }

  return "分析任务暂时无法完成，请检查输入后稍后重试。";
}

function normalizeBackendError(message: string): string {
  if (message.includes("财务分析工作流执行失败")) {
    return "后端分析工作流执行失败，请确认数据库、模型和 TuShare 等配置已准备好。";
  }

  if (message.length > 180) {
    return `${message.slice(0, 180)}...`;
  }

  return message;
}
