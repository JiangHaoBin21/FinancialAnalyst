<script setup lang="ts">
import { AlertCircle, RotateCcw } from "lucide-vue-next";

defineProps<{ message: string }>();
const emit = defineEmits<{ retry: [] }>();
</script>

<template>
  <section class="error-state" role="alert">
    <span class="error-icon"><AlertCircle :size="20" /></span>
    <div>
      <h3>这次分析没有完成</h3>
      <p>{{ message }}</p>
    </div>
    <button type="button" @click="emit('retry')">
      <RotateCcw :size="15" />重新尝试
    </button>
  </section>
</template>
