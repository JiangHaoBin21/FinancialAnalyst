<script setup lang="ts">
import { computed } from "vue";
import {
  Bot,
  CheckCircle2,
  CircleDashed,
  DatabaseZap,
  FileText,
  LineChart,
  ShieldCheck,
} from "lucide-vue-next";
import type { Component } from "vue";
import type { ExecutionRecord, FinancialAnalysisResponse } from "../types/financialAnalysis";

const props = defineProps<{
  loading?: boolean;
  response?: FinancialAnalysisResponse | null;
}>();

interface TimelineStep {
  key: string;
  label: string;
  agent: string;
  icon: Component;
}

const steps: TimelineStep[] = [
  { key: "supervisor", label: "任务规划", agent: "Supervisor", icon: Bot },
  { key: "data", label: "数据准备", agent: "DataAgent", icon: DatabaseZap },
  { key: "analysis", label: "结构化分析", agent: "AnalysisAgent", icon: LineChart },
  { key: "report", label: "报告生成", agent: "ReportAgent", icon: FileText },
  { key: "reflection", label: "反思审查", agent: "ReflectionAgent", icon: ShieldCheck },
];

const historyByStep = computed(() => {
  const map = new Map<string, ExecutionRecord>();
  for (const item of props.response?.execution_history || []) {
    if (item.step) {
      map.set(String(item.step), item);
    }
  }
  return map;
});

function getStepState(step: TimelineStep, index: number) {
  const record = historyByStep.value.get(step.key);
  if (record) {
    return record.success === false ? "failed" : "done";
  }

  if (props.response?.has_error && props.response.current_stage === step.key) {
    return "failed";
  }

  if (props.response?.current_stage === step.key || props.response?.next_step === step.key) {
    return "running";
  }

  if (props.loading) {
    return index <= 1 ? "running" : "queued";
  }

  return "queued";
}

function getMessage(step: TimelineStep) {
  const record = historyByStep.value.get(step.key);
  return record?.message || `${step.agent} 等待调度`;
}
</script>

<template>
  <section class="glass-panel rounded-lg p-5">
    <div class="mb-5 flex items-center justify-between">
      <div>
        <p class="text-xs font-semibold uppercase tracking-[0.22em] text-cyan-200">
          Agent Workflow
        </p>
        <h2 class="mt-2 text-lg font-semibold text-white">执行时间线</h2>
      </div>
      <div
        class="rounded-full border px-3 py-1 text-xs"
        :class="loading ? 'border-teal-300/40 text-teal-200' : 'border-white/10 text-slate-300'"
      >
        {{ loading ? "Running" : response?.status || "Standby" }}
      </div>
    </div>

    <div class="space-y-3">
      <div
        v-for="(step, index) in steps"
        :key="step.key"
        class="flex gap-3 rounded-lg border border-white/10 bg-white/[0.04] p-3"
      >
        <div
          class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg"
          :class="{
            'bg-teal-300/15 text-teal-200': getStepState(step, index) === 'done',
            'bg-cyan-300/15 text-cyan-200': getStepState(step, index) === 'running',
            'bg-rose-300/15 text-rose-200': getStepState(step, index) === 'failed',
            'bg-white/5 text-slate-400': getStepState(step, index) === 'queued',
          }"
        >
          <component
            :is="getStepState(step, index) === 'done' ? CheckCircle2 : getStepState(step, index) === 'running' ? CircleDashed : step.icon"
            class="h-5 w-5"
            :class="{ 'animate-spin': getStepState(step, index) === 'running' }"
          />
        </div>
        <div class="min-w-0 flex-1">
          <div class="flex items-center justify-between gap-3">
            <p class="text-sm font-semibold text-white">{{ step.label }}</p>
            <p class="text-xs text-slate-400">{{ step.agent }}</p>
          </div>
          <p class="mt-1 line-clamp-2 text-xs leading-5 text-slate-400">
            {{ getMessage(step) }}
          </p>
        </div>
      </div>
    </div>
  </section>
</template>
