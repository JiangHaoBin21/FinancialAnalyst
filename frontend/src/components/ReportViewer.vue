<script setup lang="ts">
import { computed } from "vue";
import MarkdownIt from "markdown-it";
import { FileText } from "lucide-vue-next";

const props = defineProps<{
  markdown?: string;
  title?: string;
}>();

const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
});

const html = computed(() => (props.markdown ? md.render(props.markdown) : ""));
</script>

<template>
  <section class="glass-panel rounded-lg p-5 lg:p-6">
    <div class="mb-5 flex items-center justify-between gap-4">
      <div>
        <p class="text-xs font-semibold uppercase tracking-[0.22em] text-emerald-200">
          Full Report
        </p>
        <h2 class="mt-2 text-xl font-semibold text-white">
          {{ title || "完整财务分析报告" }}
        </h2>
      </div>
      <div class="rounded-lg border border-emerald-300/20 bg-emerald-300/10 p-3 text-emerald-100">
        <FileText class="h-5 w-5" />
      </div>
    </div>

    <article
      v-if="html"
      class="report-markdown max-h-[720px] overflow-auto rounded-lg border border-white/10 bg-black/20 px-5 py-4"
      v-html="html"
    />
    <div
      v-else
      class="rounded-lg border border-dashed border-white/15 bg-white/[0.035] px-5 py-10 text-center"
    >
      <p class="text-sm text-slate-400">分析完成后，Markdown 报告会显示在这里。</p>
    </div>
  </section>
</template>
