<script setup lang="ts">
import { AlertCircle, RotateCcw } from "lucide-vue-next";

defineProps<{
  message: string;
}>();

const emit = defineEmits<{
  retry: [];
}>();
</script>

<template>
  <section class="rounded-lg border border-rose-300/25 bg-rose-300/10 p-5">
    <div class="flex gap-4">
      <div class="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-rose-300/15 text-rose-100">
        <AlertCircle class="h-5 w-5" />
      </div>
      <div class="min-w-0 flex-1">
        <h3 class="font-semibold text-white">分析任务未完成</h3>
        <p class="mt-2 text-sm leading-6 text-rose-50/85">{{ message }}</p>
        <button
          type="button"
          class="mt-4 inline-flex items-center gap-2 rounded-lg border border-rose-200/25 px-3 py-2 text-sm font-medium text-rose-50 transition hover:bg-rose-200/10"
          @click="emit('retry')"
        >
          <RotateCcw class="h-4 w-4" />
          重新尝试
        </button>
      </div>
    </div>
  </section>
</template>
