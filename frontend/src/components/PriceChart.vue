<script setup lang="ts">
/**
 * PriceChart — Componente de gráfico de preço (mockado)
 *
 * Placeholder para integração com Chart.js em SPEC_039.
 * Por enquanto exibe texto indicando que está em desenvolvimento.
 */

interface PriceChartProps {
  prices?: number[];
  labels?: string[];
  loading: boolean;
}

withDefaults(defineProps<PriceChartProps>(), {
  prices: () => [],
  labels: () => [],
  loading: false,
});
</script>

<template>
  <div class="price-chart">
    <div v-if="loading" class="price-chart__placeholder">Carregando gráfico...</div>
    <div v-else class="price-chart__placeholder">
      <div class="price-chart__icon">📊</div>
      <p class="price-chart__text">Gráfico de preço em desenvolvimento</p>
      <p class="price-chart__note">Será implementado com Chart.js em SPEC_039</p>
    </div>
  </div>
</template>

<style scoped>
.price-chart {
  background: #fff;
  border-radius: 8px;
  padding: 32px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.price-chart__placeholder {
  text-align: center;
}

.price-chart__icon {
  font-size: 32px;
  margin-bottom: 12px;
}

.price-chart__text {
  font-size: 16px;
  color: var(--color-text);
  margin: 0 0 4px;
}

.price-chart__note {
  font-size: 13px;
  color: #999;
  font-style: italic;
  margin: 0;
}
</style>
