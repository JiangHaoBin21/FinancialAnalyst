<script setup lang="ts">
import { computed } from "vue";
import type { Component } from "vue";
import {
  BarChart3,
  Building2,
  Check,
  CheckCircle2,
  ClipboardList,
  Database,
  FileText,
  GitBranch,
  Merge,
  RefreshCcw,
  SearchCheck,
  ShieldCheck,
  Sparkles,
  Table2,
} from "lucide-vue-next";
import type { ExecutionRecord, FinancialAnalysisResponse } from "../types/financialAnalysis";

const props = defineProps<{
  response?: FinancialAnalysisResponse | null;
}>();

type FlowState = "done" | "failed";

interface FlowStage {
  key: string;
  label: string;
  description: string;
  icon: Component;
  state: FlowState;
}

interface DataPart {
  key: string;
  label: string;
  icon: Component;
  state: FlowState;
  runs: number;
}

const records = computed(() => props.response?.execution_history || []);

function recordsForAgent(agent: string): ExecutionRecord[] {
  return records.value.filter((record) => record.agent === agent);
}

function stateOf(items: ExecutionRecord[]): FlowState {
  return items.some((item) => item.success === false) ? "failed" : "done";
}

const supervisorRecords = computed(() => recordsForAgent("SupervisorAgent"));
const supervisorReviewCount = computed(() => Math.max(0, supervisorRecords.value.length - 1));

const reviewCountByStage = computed(() => {
  const counts: Record<string, number> = {};
  let latestStage = "";
  let seenInitialSupervisor = false;

  for (const record of records.value) {
    if (record.agent === "SupervisorAgent") {
      if (!seenInitialSupervisor) {
        seenInitialSupervisor = true;
      } else if (latestStage) {
        counts[latestStage] = (counts[latestStage] || 0) + 1;
      }
      continue;
    }

    if (record.step && ["data", "analysis", "report", "reflection"].includes(record.step)) {
      latestStage = record.step;
    }
  }

  return counts;
});

const mainStages = computed<FlowStage[]>(() => {
  const definitions: Array<Omit<FlowStage, "state"> & { records: ExecutionRecord[] }> = [
    {
      key: "supervisor",
      label: "任务规划",
      description: "识别意图并编排任务",
      icon: ClipboardList,
      records: supervisorRecords.value.slice(0, 1),
    },
    {
      key: "data",
      label: "数据准备",
      description: "按需并行获取并校验",
      icon: Database,
      records: records.value.filter((record) => record.step === "data"),
    },
    {
      key: "analysis",
      label: "财务分析",
      description: "提炼指标与财务证据",
      icon: BarChart3,
      records: recordsForAgent("AnalysisAgent"),
    },
    {
      key: "report",
      label: "报告生成",
      description: "组织结论与完整报告",
      icon: FileText,
      records: recordsForAgent("ReportAgent"),
    },
    {
      key: "reflection",
      label: "结论复核",
      description: "检查风险与结论质量",
      icon: ShieldCheck,
      records: recordsForAgent("ReflectionAgent"),
    },
    {
      key: "finished",
      label: "流程完成",
      description: "分析结果已交付",
      icon: CheckCircle2,
      records: records.value.filter(
        (record) => record.step === "finished" || (record.agent === "System" && record.success),
      ),
    },
  ];

  return definitions
    .filter((stage) => stage.records.length)
    .map(({ records: stageRecords, ...stage }) => ({
      ...stage,
      state: stateOf(stageRecords),
    }));
});

const dataParts = computed<DataPart[]>(() => {
  const definitions = [
    { key: "income_statements", label: "利润表", icon: Table2 },
    { key: "balance_sheets", label: "资产负债表", icon: Table2 },
    { key: "cashflow_statements", label: "现金流量表", icon: Table2 },
    { key: "financial_indicators", label: "财务指标", icon: BarChart3 },
  ];

  return definitions.flatMap((definition) => {
    const partRecords = records.value.filter(
      (record) =>
        record.agent === `DataNode:${definition.key}` ||
        record.metadata?.part_name === definition.key,
    );

    if (!partRecords.length) return [];

    return [{
      ...definition,
      state: stateOf(partRecords),
      runs: partRecords.length,
    }];
  });
});

const companyContext = computed(() => recordsForAgent("DataNode:company context"));
const dataPlanning = computed(() => recordsForAgent("DataAgent"));
const mergeRecords = computed(() => recordsForAgent("DataNode:merge node"));
const checkRecords = computed(() => recordsForAgent("DataNode:completeness check"));
const backfillRecords = computed(() => recordsForAgent("DataNode:backfill plan"));
const finalizeRecords = computed(() => recordsForAgent("DataNode:finalize"));
const hasDataDetails = computed(
  () =>
    dataPlanning.value.length > 0 ||
    companyContext.value.length > 0 ||
    dataParts.value.length > 0 ||
    mergeRecords.value.length > 0 ||
    checkRecords.value.length > 0 ||
    finalizeRecords.value.length > 0,
);
const dataRounds = computed(() => Math.max(1, mergeRecords.value.length));
</script>

<template>
  <section v-if="mainStages.length" class="workflow-card">
    <header class="workflow-header">
      <div>
        <p class="section-kicker">EXECUTION TRACE</p>
        <h2>本次报告的生成流程</h2>
      </div>
      <div class="workflow-summary-badge">
        <Sparkles :size="14" />
        {{ mainStages.length }} 个主阶段
        <span v-if="supervisorReviewCount">· {{ supervisorReviewCount }} 次阶段复核</span>
      </div>
    </header>

    <div class="main-flow" aria-label="报告生成主流程">
      <article
        v-for="(stage, index) in mainStages"
        :key="stage.key"
        class="main-flow-stage"
        :class="`flow-${stage.state}`"
      >
        <span class="stage-icon"><component :is="stage.icon" :size="18" /></span>
        <div>
          <strong>{{ stage.label }}</strong>
          <small>{{ stage.description }}</small>
        </div>
        <span class="stage-check"><Check :size="12" /></span>
        <span
          v-if="index < mainStages.length - 1 && reviewCountByStage[stage.key]"
          class="review-chip"
        >
          <ShieldCheck :size="11" />Supervisor 复核
        </span>
      </article>
    </div>

    <section v-if="hasDataDetails" class="data-trace">
      <header class="data-trace-header">
        <div>
          <span class="data-title-icon"><GitBranch :size="17" /></span>
          <div>
            <strong>数据准备内部流程</strong>
            <small>财务数据按需求拆分，多路并行读取后统一汇合校验</small>
          </div>
        </div>
        <span v-if="dataRounds > 1" class="round-badge">
          <RefreshCcw :size="12" />{{ dataRounds }} 轮数据获取
        </span>
      </header>

      <div class="data-flow">
        <div class="data-flow-row data-flow-collect">
          <article v-if="dataPlanning.length" class="data-node">
            <span><ClipboardList :size="16" /></span>
            <div><strong>需求规划</strong><small>确定所需数据</small></div>
          </article>

          <i v-if="dataPlanning.length && companyContext.length" class="data-arrow" />

          <article v-if="companyContext.length" class="data-node">
            <span><Building2 :size="16" /></span>
            <div><strong>公司识别</strong><small>匹配公司与代码</small></div>
          </article>

          <i v-if="companyContext.length && dataParts.length" class="data-arrow data-arrow-split" />

          <div v-if="dataParts.length" class="parallel-group">
            <div class="parallel-label">
              <GitBranch :size="12" />{{ dataParts.length }} 路并行
            </div>
            <div class="parallel-parts">
              <article
                v-for="part in dataParts"
                :key="part.key"
                class="parallel-part"
                :class="`part-${part.state}`"
              >
                <component :is="part.icon" :size="14" />
                <span>{{ part.label }}</span>
                <small v-if="part.runs > 1">含 {{ part.runs - 1 }} 次回源</small>
                <Check v-else :size="11" />
              </article>
            </div>
          </div>
        </div>

        <div class="data-flow-turn" aria-hidden="true">
          <span><Merge :size="12" />并行结果汇合后进入校验</span>
        </div>

        <div class="data-flow-row data-flow-validate">
          <article v-if="mergeRecords.length" class="data-node">
            <span><Merge :size="16" /></span>
            <div>
              <strong>数据汇合</strong>
              <small>{{ mergeRecords.length > 1 ? `${mergeRecords.length} 轮合并` : "合并并行结果" }}</small>
            </div>
          </article>

          <i v-if="mergeRecords.length && checkRecords.length" class="data-arrow" />

          <article v-if="checkRecords.length" class="data-node">
            <span><SearchCheck :size="16" /></span>
            <div>
              <strong>完整性检查</strong>
              <small>{{ checkRecords.length > 1 ? `${checkRecords.length} 轮校验` : "识别缺失数据" }}</small>
            </div>
          </article>

          <template v-if="backfillRecords.length">
            <i class="data-arrow" />
            <article class="data-node">
              <span><RefreshCcw :size="16" /></span>
              <div>
                <strong>回源评估</strong>
                <small>{{ dataRounds > 1 ? "已补充缺失数据" : "无需额外补充" }}</small>
              </div>
            </article>
          </template>

          <template v-if="finalizeRecords.length">
            <i class="data-arrow" />
            <article class="data-node data-node-final">
              <span><CheckCircle2 :size="16" /></span>
              <div><strong>数据就绪</strong><small>交付分析阶段</small></div>
            </article>
          </template>
        </div>
      </div>
    </section>
  </section>
</template>
