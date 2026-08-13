<script setup lang="ts">
import { computed, nextTick, ref } from "vue";
import { Activity, BarChart3, Database, FileText, ShieldCheck } from "lucide-vue-next";
import { createFinancialAnalysis, getFriendlyApiError } from "../api/financialAnalysis";
import AgentTimeline from "../components/AgentTimeline.vue";
import AnalysisForm from "../components/AnalysisForm.vue";
import ErrorState from "../components/ErrorState.vue";
import LoadingState from "../components/LoadingState.vue";
import MetricCard from "../components/MetricCard.vue";
import ReportViewer from "../components/ReportViewer.vue";
import RiskPanel from "../components/RiskPanel.vue";
import type { AnalysisFormPayload, FinancialAnalysisResponse } from "../types/financialAnalysis";
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
  compactText(response.value?.report_result?.title, "财务分析报告"),
);
const scoreLabel = computed(() =>
  compactText(overallScore.value?.label, "分析完成"),
);
const scoreBasis = computed(() =>
  compactText(overallScore.value?.basis, "综合财务数据与分析结论得出。"),
);
const metrics = computed(() => collectMetrics(response.value));
const riskWarnings = computed(() => response.value?.report_result?.risk_warnings || []);
const dataLimitations = computed(() => {
  const reportItems = response.value?.report_result?.data_limitations || [];
  const analysisItems = response.value?.analysis_result?.data_limitations || [];
  return Array.from(new Set([...reportItems, ...analysisItems].filter(Boolean)));
});
const hasRiskContent = computed(
  () => riskWarnings.value.length > 0 || dataLimitations.value.length > 0,
);

async function handleSubmit(payload: AnalysisFormPayload) {
  lastPayload.value = payload;
  await runAnalysis(payload);
}

async function retryLastTask() {
  if (lastPayload.value) await runAnalysis(lastPayload.value);
}

async function runAnalysis(payload: AnalysisFormPayload) {
  loading.value = true;
  errorMessage.value = "";
  response.value = null;

  try {
    const result = await createFinancialAnalysis({
      query: payload.query,
      include_state: false,
    });
    response.value = result;

    if (result.has_error) {
      errorMessage.value =
        result.error_message || result.assistant_message || "分析流程未能完成，请稍后重试。";
    }
  } catch (error) {
    errorMessage.value = getFriendlyApiError(error);
  } finally {
    loading.value = false;
    await nextTick();
    resultRef.value?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}
</script>

<template>
  <main class="app-shell">
    <nav class="topbar" aria-label="主导航">
      <a class="brand" href="#" aria-label="观澜财务分析首页">
        <span class="brand-mark"><BarChart3 :size="19" /></span>
        <span>观澜</span>
        <span class="brand-divider" />
        <span class="brand-subtitle">财务研究助手</span>
      </a>
      <div class="service-status">
        <span class="status-dot" />
        AI 分析服务
      </div>
    </nav>

    <section class="hero-section">
      <div class="eyebrow">AI-POWERED FINANCIAL RESEARCH</div>
      <h1>把财报，变成<br /><em>可行动的判断。</em></h1>
      <p class="hero-copy">
        用自然语言提出问题。系统会自动完成数据准备、财务分析、风险审查和报告生成。
      </p>

      <AnalysisForm :loading="loading" @submit="handleSubmit" />

      <div class="trust-row" aria-label="产品能力">
        <span><Database :size="15" />真实财务数据</span>
        <span><Activity :size="15" />多智能体协作</span>
        <span><ShieldCheck :size="15" />结论复核</span>
      </div>
    </section>

    <section v-if="loading || response || errorMessage" ref="resultRef" class="result-section">
      <LoadingState v-if="loading" />

      <ErrorState
        v-else-if="errorMessage && !response"
        :message="errorMessage"
        @retry="retryLastTask"
      />

      <template v-if="response && !loading">
        <header class="result-header">
          <div>
            <p class="section-kicker">ANALYSIS COMPLETE</p>
            <h2>{{ reportTitle }}</h2>
          </div>
          <div class="result-status"><span />分析完成</div>
        </header>

        <ErrorState
          v-if="errorMessage"
          :message="errorMessage"
          @retry="retryLastTask"
        />

        <section class="overview-card">
          <div class="score-panel">
            <p class="panel-label">综合评价</p>
            <div class="score-value">
              {{ formatScore(overallScore) }}<small v-if="formatScore(overallScore) !== '--'">/100</small>
            </div>
            <span class="score-tag">{{ scoreLabel }}</span>
            <p>{{ scoreBasis }}</p>
          </div>

          <div class="summary-panel">
            <p class="panel-label">核心结论</p>
            <p class="summary-copy">{{ summary }}</p>

            <div v-if="metrics.length" class="metric-grid">
              <MetricCard
                v-for="(metric, index) in metrics"
                :key="`${metric.name}-${index}`"
                :title="metric.name || '关键指标'"
                :value="formatMetricValue(metric)"
                :description="metric.period || '报告期'"
                :accent="index % 3 === 0 ? 'blue' : index % 3 === 1 ? 'gold' : 'green'"
              />
            </div>
          </div>
        </section>

        <RiskPanel
          v-if="hasRiskContent"
          :risk-warnings="riskWarnings"
          :data-limitations="dataLimitations"
        />

        <ReportViewer
          v-if="reportMarkdown"
          :markdown="reportMarkdown"
          :title="reportTitle"
        />

        <AgentTimeline :response="response" />
      </template>
    </section>

    <footer class="page-footer">
      <FileText :size="15" />
      分析结果仅供研究参考，不构成投资建议
    </footer>
  </main>
</template>
