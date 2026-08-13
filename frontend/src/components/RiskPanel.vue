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
  <div class="risk-grid">
    <section v-if="risks.length" class="risk-card risk-warning">
      <div class="risk-title"><AlertTriangle :size="18" />需要关注的风险</div>
      <ul>
        <li v-for="risk in risks" :key="risk">{{ risk }}</li>
      </ul>
    </section>

    <section v-if="limitations.length" class="risk-card risk-info">
      <div class="risk-title"><Info :size="18" />数据与结论边界</div>
      <ul>
        <li v-for="item in limitations" :key="item">{{ item }}</li>
      </ul>
    </section>
  </div>
</template>
