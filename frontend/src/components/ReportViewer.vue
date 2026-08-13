<script setup lang="ts">
import { computed, ref } from "vue";
import MarkdownIt from "markdown-it";
import { Check, Clipboard, FileText } from "lucide-vue-next";

const props = defineProps<{ markdown?: string; title?: string }>();
const copied = ref(false);
const md = new MarkdownIt({ html: false, linkify: true, breaks: true });
const html = computed(() => (props.markdown ? md.render(props.markdown) : ""));

async function copyReport() {
  if (!props.markdown) return;
  await navigator.clipboard.writeText(props.markdown);
  copied.value = true;
  window.setTimeout(() => (copied.value = false), 1600);
}
</script>

<template>
  <section class="report-card">
    <header class="report-header">
      <div>
        <p class="section-kicker">FULL REPORT</p>
        <h2><FileText :size="20" />完整分析报告</h2>
      </div>
      <button class="copy-button" type="button" @click="copyReport">
        <Check v-if="copied" :size="15" />
        <Clipboard v-else :size="15" />
        {{ copied ? "已复制" : "复制报告" }}
      </button>
    </header>
    <article class="report-markdown" v-html="html" />
  </section>
</template>
