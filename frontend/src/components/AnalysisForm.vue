<script setup lang="ts">
import { computed, reactive } from "vue";
import {
  BarChart3,
  CalendarDays,
  ChevronRight,
  CircleDollarSign,
  MessageSquareText,
  Settings2,
} from "lucide-vue-next";
import type { AnalysisFormPayload } from "../types/financialAnalysis";

const emit = defineEmits<{
  submit: [payload: AnalysisFormPayload];
}>();

const props = defineProps<{
  loading?: boolean;
}>();

const focusOptions = ["综合分析", "盈利能力", "偿债能力", "现金流", "经营质量"];

const form = reactive<AnalysisFormPayload>({
  company: "宁德时代",
  year: "2023",
  focus: "综合分析",
  question: "请分析该公司的财务表现，并生成一份适合管理层阅读的财务分析报告。",
  includeState: false,
});

const errors = reactive({
  company: "",
  year: "",
  question: "",
});

const canSubmit = computed(() => !props.loading);

function validate(): boolean {
  errors.company = form.company.trim() ? "" : "请输入公司名称或股票代码";
  errors.year = /^\d{4}$/.test(form.year.trim()) ? "" : "请输入 4 位年份";
  errors.question = form.question.trim() ? "" : "请输入分析问题";

  return !errors.company && !errors.year && !errors.question;
}

function handleSubmit() {
  if (!validate() || props.loading) {
    return;
  }

  emit("submit", {
    company: form.company.trim(),
    year: form.year.trim(),
    focus: form.focus,
    question: form.question.trim(),
    includeState: form.includeState,
  });
}
</script>

<template>
  <section class="glass-panel rounded-lg p-5 lg:p-6">
    <div class="mb-5 flex items-center justify-between gap-4">
      <div>
        <p class="text-xs font-semibold uppercase tracking-[0.22em] text-teal-200">
          Task Console
        </p>
        <h2 class="mt-2 text-xl font-semibold text-white">创建分析任务</h2>
      </div>
      <div class="rounded-lg border border-teal-300/20 bg-teal-300/10 p-3 text-teal-100">
        <Settings2 class="h-5 w-5" />
      </div>
    </div>

    <form class="space-y-5" @submit.prevent="handleSubmit">
      <label class="block">
        <span class="mb-2 flex items-center gap-2 text-sm font-medium text-slate-200">
          <CircleDollarSign class="h-4 w-4 text-teal-300" />
          公司名称或股票代码
        </span>
        <input
          v-model="form.company"
          class="w-full rounded-lg border border-white/10 bg-white/[0.06] px-4 py-3 text-sm text-white outline-none transition placeholder:text-slate-500 focus:border-teal-300/70 focus:bg-white/[0.09]"
          placeholder="例如：宁德时代 / 300750.SZ"
          :disabled="loading"
        />
        <p v-if="errors.company" class="mt-2 text-xs text-rose-300">
          {{ errors.company }}
        </p>
      </label>

      <label class="block">
        <span class="mb-2 flex items-center gap-2 text-sm font-medium text-slate-200">
          <CalendarDays class="h-4 w-4 text-cyan-300" />
          年份
        </span>
        <input
          v-model="form.year"
          class="w-full rounded-lg border border-white/10 bg-white/[0.06] px-4 py-3 text-sm text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-300/70 focus:bg-white/[0.09]"
          placeholder="例如：2023"
          inputmode="numeric"
          :disabled="loading"
        />
        <p v-if="errors.year" class="mt-2 text-xs text-rose-300">
          {{ errors.year }}
        </p>
      </label>

      <div>
        <span class="mb-2 flex items-center gap-2 text-sm font-medium text-slate-200">
          <BarChart3 class="h-4 w-4 text-amber-300" />
          分析重点
        </span>
        <div class="grid grid-cols-2 gap-2 sm:grid-cols-3">
          <button
            v-for="option in focusOptions"
            :key="option"
            type="button"
            class="rounded-lg border px-3 py-2 text-sm transition"
            :class="
              form.focus === option
                ? 'border-teal-300/70 bg-teal-300/15 text-teal-50'
                : 'border-white/10 bg-white/[0.04] text-slate-300 hover:border-white/20 hover:bg-white/[0.08]'
            "
            :disabled="loading"
            @click="form.focus = option"
          >
            {{ option }}
          </button>
        </div>
      </div>

      <label class="block">
        <span class="mb-2 flex items-center gap-2 text-sm font-medium text-slate-200">
          <MessageSquareText class="h-4 w-4 text-emerald-300" />
          分析问题
        </span>
        <textarea
          v-model="form.question"
          class="min-h-32 w-full resize-none rounded-lg border border-white/10 bg-white/[0.06] px-4 py-3 text-sm leading-6 text-white outline-none transition placeholder:text-slate-500 focus:border-emerald-300/70 focus:bg-white/[0.09]"
          placeholder="请输入希望 Agent 回答的问题"
          :disabled="loading"
        />
        <p v-if="errors.question" class="mt-2 text-xs text-rose-300">
          {{ errors.question }}
        </p>
      </label>

      <label class="flex items-center justify-between gap-4 rounded-lg border border-white/10 bg-white/[0.04] px-4 py-3">
        <span>
          <span class="block text-sm font-medium text-white">返回调试状态</span>
          <span class="text-xs text-slate-400">用于开发联调，演示时可保持关闭</span>
        </span>
        <input
          v-model="form.includeState"
          type="checkbox"
          class="h-5 w-5 rounded border-white/20 bg-transparent accent-teal-300"
          :disabled="loading"
        />
      </label>

      <button
        type="submit"
        class="flex w-full items-center justify-center gap-2 rounded-lg bg-teal-300 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-teal-200 disabled:cursor-not-allowed disabled:bg-slate-600 disabled:text-slate-300"
        :disabled="!canSubmit"
      >
        <span>{{ loading ? "Agent 分析中" : "开始分析" }}</span>
        <ChevronRight class="h-4 w-4" />
      </button>
    </form>
  </section>
</template>
