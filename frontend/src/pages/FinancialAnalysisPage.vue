<script setup lang="ts">
import { computed, nextTick, ref } from "vue";
import {
  Activity,
  Bot,
  CircuitBoard,
  FileCheck2,
  Gauge,
  Sparkles,
} from "lucide-vue-next";
import { createFinancialAnalysis, getFriendlyApiError } from "../api/financialAnalysis";
import AgentTimeline from "../components/AgentTimeline.vue";
import AnalysisForm from "../components/AnalysisForm.vue";
import ErrorState from "../components/ErrorState.vue";
import LoadingState from "../components/LoadingState.vue";
import MetricCard from "../components/MetricCard.vue";
import ReportViewer from "../components/ReportViewer.vue";
import RiskPanel from "../components/RiskPanel.vue";
import type {
  AnalysisFormPayload,
  FinancialAnalysisResponse,
} from "../types/financialAnalysis";
import {
  collectMetrics,
  compactText,
  formatMetricValue,
  formatScore,
  getOverallScore,
  getReportMarkdown,
  getSummary,
} from "../utils/formatters";

const loading = ref(false);
const errorMessage = ref("");
const response = ref<FinancialAnalysisResponse | null>(null);
const resultRef = ref<HTMLElement | null>(null);
const lastPayload = ref<AnalysisFormPayload | null>(null);

const overallScore = computed(() => getOverallScore(response.value));
const summary = computed(() => getSummary(response.value));
const reportMarkdown = computed(() => getReportMarkdown(response.value));
const reportTitle = computed(() =>
  compactText(response.value?.report_result?.title, "AI 财务分析报告"),
);

const scoreLabel = computed(() =>
  compactText(overallScore.value?.label, response.value ? "已生成" : "待分析"),
);

const scoreBasis = computed(() =>
  compactText(overallScore.value?.basis, "提交任务后，系统会给出评分依据。"),
);

const metrics = computed(() => collectMetrics(response.value));

const riskWarnings = computed(() => response.value?.report_result?.risk_warnings || []);
const dataLimitations = computed(() => {
  const reportItems = response.value?.report_result?.data_limitations || [];
  const analysisItems = response.value?.analysis_result?.data_limitations || [];
  return Array.from(new Set([...reportItems, ...analysisItems].filter(Boolean)));
});

const statusText = computed(() => {
  if (loading.value) {
    return "Agent Running";
  }
  if (response.value?.has_error) {
    return "Workflow Error";
  }
  if (response.value?.status) {
    return response.value.status;
  }
  return "Ready";
});

async function handleSubmit(payload: AnalysisFormPayload) {
  lastPayload.value = payload;
  await runAnalysis(payload);
}

async function retryLastTask() {
  if (lastPayload.value) {
    await runAnalysis(lastPayload.value);
  }
}

async function runAnalysis(payload: AnalysisFormPayload) {
  loading.value = true;
  errorMessage.value = "";
  response.value = null;

  try {
    const result = await createFinancialAnalysis({
      query: buildQuery(payload),
      include_state: payload.includeState,
    });
    response.value = result;

    if (result.has_error) {
      errorMessage.value =
        result.error_message ||
        result.assistant_message ||
        "工作流返回错误状态，请查看后端日志获取更多信息。";
    }
  } catch (error) {
    errorMessage.value = getFriendlyApiError(error);
  } finally {
    loading.value = false;
    await nextTick();
    resultRef.value?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function buildQuery(payload: AnalysisFormPayload): string {
  return [
    `公司名称或股票代码：${payload.company}`,
    `分析年份：${payload.year}`,
    `分析重点：${payload.focus}`,
    `分析问题：${payload.question}`,
    "请基于可用财务数据生成结构化结论、风险提示、数据限制和 Markdown 报告。",
  ].join("\n");
}
</script>

<template>
  <main class="min-h-screen px-4 py-6 text-slate-100 sm:px-6 lg:px-8">
    <div class="mx-auto max-w-7xl">
      <header class="mb-6 overflow-hidden rounded-lg border border-white/10 bg-white/[0.04] p-5 shadow-soft lg:p-6">
        <div class="grid gap-6 lg:grid-cols-[1.4fr_0.9fr] lg:items-center">
          <div>
            <div class="mb-4 inline-flex items-center gap-2 rounded-full border border-teal-300/25 bg-teal-300/10 px-3 py-1 text-xs font-medium text-teal-100">
              <Sparkles class="h-3.5 w-3.5" />
              AI Agent Financial Intelligence
            </div>
            <h1 class="max-w-4xl text-3xl font-bold tracking-normal text-white md:text-4xl">
              Multi-Agent Financial Analysis Platform
            </h1>
            <p class="mt-3 max-w-3xl text-sm leading-6 text-slate-300 md:text-base">
              基于多 Agent 工作流的自动化财务分析系统，串联任务规划、数据准备、结构化分析、报告生成和反思审查。
            </p>
          </div>

          <div class="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-2">
            <div class="rounded-lg border border-white/10 bg-black/20 p-4">
              <Bot class="mb-3 h-5 w-5 text-teal-200" />
              <p class="text-xs text-slate-400">Agents</p>
              <p class="mt-1 text-xl font-semibold text-white">5</p>
            </div>
            <div class="rounded-lg border border-white/10 bg-black/20 p-4">
              <Activity class="mb-3 h-5 w-5 text-cyan-200" />
              <p class="text-xs text-slate-400">Status</p>
              <p class="mt-1 truncate text-xl font-semibold text-white">{{ statusText }}</p>
            </div>
            <div class="rounded-lg border border-white/10 bg-black/20 p-4">
              <CircuitBoard class="mb-3 h-5 w-5 text-amber-200" />
              <p class="text-xs text-slate-400">Mode</p>
              <p class="mt-1 text-xl font-semibold text-white">Sync</p>
            </div>
            <div class="rounded-lg border border-white/10 bg-black/20 p-4">
              <FileCheck2 class="mb-3 h-5 w-5 text-emerald-200" />
              <p class="text-xs text-slate-400">Output</p>
              <p class="mt-1 text-xl font-semibold text-white">Report</p>
            </div>
          </div>
        </div>
      </header>

      <div class="grid gap-5 lg:grid-cols-[390px_minmax(0,1fr)]">
        <div class="space-y-5">
          <AnalysisForm :loading="loading" @submit="handleSubmit" />
          <AgentTimeline :loading="loading" :response="response" />
        </div>

        <section ref="resultRef" class="space-y-5">
          <LoadingState v-if="loading" />

          <ErrorState
            v-if="errorMessage && !loading"
            :message="errorMessage"
            @retry="retryLastTask"
          />

          <section class="glass-panel rounded-lg p-5 lg:p-6">
            <div class="grid gap-5 xl:grid-cols-[280px_minmax(0,1fr)]">
              <div class="rounded-lg border border-white/10 bg-white/[0.04] p-5">
                <div class="mb-4 flex items-center justify-between gap-3">
                  <div>
                    <p class="text-xs font-semibold uppercase tracking-[0.22em] text-teal-200">
                      Overall
                    </p>
                    <h2 class="mt-2 text-lg font-semibold text-white">总体评估</h2>
                  </div>
                  <Gauge class="h-5 w-5 text-teal-200" />
                </div>
                <div class="flex items-end gap-2">
                  <p class="text-5xl font-bold text-white">{{ formatScore(overallScore) }}</p>
                  <p class="pb-2 text-sm text-slate-400">/ 100</p>
                </div>
                <div class="mt-4 inline-flex rounded-full border border-teal-300/25 bg-teal-300/10 px-3 py-1 text-sm font-medium text-teal-100">
                  {{ scoreLabel }}
                </div>
                <p class="mt-4 text-sm leading-6 text-slate-400">
                  {{ scoreBasis }}
                </p>
              </div>

              <div class="min-w-0">
                <p class="text-xs font-semibold uppercase tracking-[0.22em] text-cyan-200">
                  Executive Summary
                </p>
                <h2 class="mt-2 text-2xl font-semibold text-white">
                  {{ reportTitle }}
                </h2>
                <p class="mt-4 text-sm leading-7 text-slate-300">
                  {{ summary }}
                </p>

                <div class="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                  <MetricCard
                    v-for="(metric, index) in metrics"
                    :key="`${metric.name}-${index}`"
                    :title="metric.name || '关键指标'"
                    :value="formatMetricValue(metric)"
                    :description="metric.period || '报告期未声明'"
                    :accent="index % 4 === 0 ? 'teal' : index % 4 === 1 ? 'cyan' : index % 4 === 2 ? 'amber' : 'emerald'"
                  />
                  <MetricCard
                    v-if="!metrics.length"
                    title="关键指标"
                    value="--"
                    description="分析完成后展示来自 supporting_metrics 的指标"
                    accent="teal"
                  />
                </div>
              </div>
            </div>
          </section>

          <RiskPanel
            :risk-warnings="riskWarnings"
            :data-limitations="dataLimitations"
          />

          <ReportViewer :markdown="reportMarkdown" :title="reportTitle" />
        </section>
      </div>
    </div>
  </main>
</template>
