<script setup lang="ts">
import { computed } from "vue";
import { Activity, TrendingUp } from "lucide-vue-next";

const props = defineProps<{
  title: string;
  value: string;
  description?: string;
  accent?: "teal" | "cyan" | "amber" | "emerald";
}>();

const accentClasses = computed(() => {
  switch (props.accent) {
    case "cyan":
      return "border-cyan-300/20 bg-cyan-300/10 text-cyan-100";
    case "amber":
      return "border-amber-300/20 bg-amber-300/10 text-amber-100";
    case "emerald":
      return "border-emerald-300/20 bg-emerald-300/10 text-emerald-100";
    default:
      return "border-teal-300/20 bg-teal-300/10 text-teal-100";
  }
});
</script>

<template>
  <article class="rounded-lg border border-white/10 bg-white/[0.045] p-4">
    <div class="flex items-start justify-between gap-3">
      <div class="min-w-0">
        <p class="truncate text-sm text-slate-400">{{ title }}</p>
        <p class="mt-2 text-2xl font-semibold text-white">{{ value }}</p>
      </div>
      <div class="rounded-lg border p-2" :class="accentClasses">
        <TrendingUp v-if="value !== '--'" class="h-4 w-4" />
        <Activity v-else class="h-4 w-4" />
      </div>
    </div>
    <p class="mt-3 line-clamp-2 min-h-10 text-xs leading-5 text-slate-400">
      {{ description || "来自 Agent 结构化分析结果" }}
    </p>
  </article>
</template>
