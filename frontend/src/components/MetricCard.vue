<script setup lang="ts">
withDefaults(
  defineProps<{
    title: string;
    value: string;
    description?: string;
    accent?: "blue" | "gold" | "green";
  }>(),
  { accent: "blue" },
);
</script>

<template>
  <article class="metric-card" :class="`metric-${accent}`">
    <p>{{ title }}</p>
    <strong>{{ value }}</strong>
    <span>{{ description || "报告期" }}</span>
  </article>
</template>
