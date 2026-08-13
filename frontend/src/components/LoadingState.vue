<script setup lang="ts">
import { LoaderCircle } from "lucide-vue-next";
</script>

<template>
  <section class="loading-state" aria-live="polite">
    <span class="loading-icon"><LoaderCircle :size="22" /></span>
    <div>
      <h2>正在阅读数据并形成判断</h2>
      <p>这通常需要几分钟。请保持页面打开，完成后报告会自动显示。</p>
    </div>
    <div class="loading-bar"><span /></div>
  </section>
</template>
