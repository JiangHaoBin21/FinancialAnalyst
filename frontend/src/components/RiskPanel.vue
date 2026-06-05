<script setup lang="ts">
import { computed } from "vue";
import { AlertTriangle, Info } from "lucide-vue-next";

const props = defineProps<{
  riskWarnings?: string[];
  dataLimitations?: string[];
}>();

const risks = computed(() => props.riskWarnings?.filter(Boolean) || []);
const limitations = computed(() => props.dataLimitations?.filter(Boolean) || []);
</script>

<template>
  <div class="grid gap-4 lg:grid-cols-2">
    <section class="rounded-lg border border-amber-300/20 bg-amber-300/10 p-5">
      <div class="mb-4 flex items-center gap-2 text-amber-100">
        <AlertTriangle class="h-5 w-5" />
        <h3 class="font-semibold">风险提示</h3>
      </div>
      <ul v-if="risks.length" class="space-y-3">
        <li v-for="risk in risks" :key="risk" class="text-sm leading-6 text-amber-50/90">
          {{ risk }}
        </li>
      </ul>
      <p v-else class="text-sm text-amber-50/70">暂无明确风险提示。</p>
    </section>

    <section class="rounded-lg border border-cyan-300/20 bg-cyan-300/10 p-5">
      <div class="mb-4 flex items-center gap-2 text-cyan-100">
        <Info class="h-5 w-5" />
        <h3 class="font-semibold">数据限制</h3>
      </div>
      <ul v-if="limitations.length" class="space-y-3">
        <li
          v-for="item in limitations"
          :key="item"
          class="text-sm leading-6 text-cyan-50/90"
        >
          {{ item }}
        </li>
      </ul>
      <p v-else class="text-sm text-cyan-50/70">当前结果未声明额外数据限制。</p>
    </section>
  </div>
</template>
