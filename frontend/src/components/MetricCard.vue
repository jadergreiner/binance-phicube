<script setup lang="ts">
/**
 * MetricCard — Cartão de métrica
 *
 * Exibe label, valor e delta opcional com seta indicadora.
 */

interface MetricCardProps {
  label: string;
  value: string | number;
  delta?: number;
  unit?: string;
}

defineProps<MetricCardProps>();

function deltaArrow(delta: number): string {
  if (delta > 0) return '↑';
  if (delta < 0) return '↓';
  return '→';
}

function deltaClass(delta: number): string {
  if (delta > 0) return 'delta--positive';
  if (delta < 0) return 'delta--negative';
  return 'delta--neutral';
}
</script>

<template>
  <div class="metric-card">
    <div class="metric-card__label">{{ label }}</div>
    <div class="metric-card__value">
      {{ value }}<span v-if="unit" class="metric-card__unit">{{ unit }}</span>
    </div>
    <div v-if="delta !== undefined" class="metric-card__delta" :class="deltaClass(delta)">
      {{ deltaArrow(delta) }}
      {{ delta >= 0 ? '+' : '' }}{{ delta.toFixed(1) }}{{ unit || '' }}
    </div>
  </div>
</template>

<style scoped>
.metric-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-card__label {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #666;
}

.metric-card__value {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text);
  line-height: 1.2;
}

.metric-card__unit {
  font-size: 14px;
  font-weight: 500;
  color: #999;
  margin-left: 4px;
}

.metric-card__delta {
  font-size: 13px;
  font-weight: 600;
  margin-top: 4px;
}

.delta--positive {
  color: var(--color-success);
}

.delta--negative {
  color: var(--color-danger);
}

.delta--neutral {
  color: #999;
}
</style>
