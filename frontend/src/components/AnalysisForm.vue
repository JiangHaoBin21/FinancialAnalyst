<script setup lang="ts">
import { computed, ref } from "vue";
import { ArrowUpRight, Command, Sparkles } from "lucide-vue-next";
import type { AnalysisFormPayload } from "../types/financialAnalysis";

const props = defineProps<{
  loading?: boolean;
}>();

const emit = defineEmits<{
  submit: [payload: AnalysisFormPayload];
}>();

const query = ref("");
const error = ref("");
const canSubmit = computed(() => Boolean(query.value.trim()) && !props.loading);

function handleSubmit() {
  if (!query.value.trim()) {
    error.value = "请先告诉我你想分析哪家公司，以及关注什么问题。";
    return;
  }

  if (props.loading) return;

  error.value = "";
  emit("submit", { query: query.value.trim() });
}

function handleKeydown(event: KeyboardEvent) {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    event.preventDefault();
    handleSubmit();
  }
}
</script>

<template>
  <form class="analysis-composer" @submit.prevent="handleSubmit">
    <div class="composer-heading">
      <span class="composer-icon"><Sparkles :size="18" /></span>
      <span>开始一次深度分析</span>
    </div>

    <label class="sr-only" for="analysis-query">分析需求</label>
    <textarea
      id="analysis-query"
      v-model="query"
      rows="5"
      :disabled="loading"
      placeholder="例如：分析宁德时代 2023 年的盈利能力、现金流和主要风险，并给出面向管理层的结论。"
      @keydown="handleKeydown"
    />

    <p v-if="error" class="form-error">{{ error }}</p>

    <div class="composer-footer">
      <p class="composer-tip">
        <Command :size="14" />
        写明公司、报告期和关注点，结果会更准确
      </p>
      <button type="submit" class="primary-button" :disabled="!canSubmit">
        <span>{{ loading ? "分析进行中" : "开始分析" }}</span>
        <span class="button-icon"><ArrowUpRight :size="17" /></span>
      </button>
    </div>
  </form>
</template>
