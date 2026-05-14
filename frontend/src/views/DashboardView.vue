<script setup lang="ts">
/**
 * DashboardView — Tela principal do dashboard
 *
 * Exibe métricas de performance, tabelas por símbolo e timeframe.
 * Atualiza automaticamente a cada 60 segundos.
 */
import { onMounted, onUnmounted } from 'vue';
import { usePositionStore } from '@/stores/positionStore';
import { usePerformanceStore } from '@/stores/performanceStore';
import MetricCard from '@/components/MetricCard.vue';
import LoadingSpinner from '@/components/LoadingSpinner.vue';
import ErrorBanner from '@/components/ErrorBanner.vue';

const positionStore = usePositionStore();
const performanceStore = usePerformanceStore();

let pollingInterval: ReturnType<typeof setInterval> | null = null;

onMounted(async () => {
  await Promise.all([positionStore.fetchPositions(), performanceStore.fetchPerformance()]);
  pollingInterval = setInterval(async () => {
    await Promise.all([positionStore.fetchPositions(), performanceStore.fetchPerformance()]);
  }, 60000);
});

onUnmounted(() => {
  if (pollingInterval) clearInterval(pollingInterval);
});

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'USD',
  }).format(value);
}
</script>

<template>
  <div class="dashboard">
    <h1 class="dashboard__title">Dashboard</h1>

    <ErrorBanner
      v-if="positionStore.error"
      :message="positionStore.error"
      type="error"
      @close="positionStore.error = null"
    />
    <ErrorBanner
      v-if="performanceStore.error"
      :message="performanceStore.error"
      type="error"
      @close="performanceStore.error = null"
    />

    <LoadingSpinner v-if="performanceStore.loading" size="large" />

    <div v-else class="dashboard__metrics">
      <MetricCard
        label="Total de Trades"
        :value="performanceStore.globalMetrics?.total_trades ?? 0"
      />
      <MetricCard
        label="Win Rate"
        :value="performanceStore.globalMetrics?.win_rate_pct ?? 0"
        unit="%"
        :delta="(performanceStore.globalMetrics?.win_rate_pct ?? 0) - 50"
      />
      <MetricCard
        label="P&L Total"
        :value="formatCurrency(performanceStore.globalMetrics?.total_pnl_usdt ?? 0)"
        :delta="performanceStore.globalMetrics?.total_pnl_usdt ?? 0"
      />
      <MetricCard
        label="RRR Médio"
        :value="performanceStore.globalMetrics?.avg_rrr ?? 0"
        unit="x"
      />
      <MetricCard
        label="Max Drawdown"
        :value="formatCurrency(performanceStore.globalMetrics?.max_drawdown_usdt ?? 0)"
      />
      <MetricCard
        label="Profit Factor"
        :value="performanceStore.globalMetrics?.profit_factor ?? 0"
        unit="x"
      />
    </div>

    <div v-if="performanceStore.data?.by_symbol" class="dashboard__section">
      <h2 class="dashboard__subtitle">Performance por Símbolo</h2>
      <table class="dashboard__table">
        <thead>
          <tr>
            <th>Símbolo</th>
            <th>Trades</th>
            <th>Win Rate</th>
            <th>P&L</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in performanceStore.data.by_symbol" :key="s.symbol">
            <td>{{ s.symbol }}</td>
            <td>{{ s.total_trades }}</td>
            <td>{{ s.win_rate_pct.toFixed(1) }}%</td>
            <td :class="s.total_pnl_usdt >= 0 ? 'text-success' : 'text-danger'">
              {{ formatCurrency(s.total_pnl_usdt) }}
            </td>
          </tr>
          <tr v-if="!performanceStore.data.by_symbol.length">
            <td colspan="4" class="text-muted">Nenhum dado disponível</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="performanceStore.data?.by_timeframe" class="dashboard__section">
      <h2 class="dashboard__subtitle">Performance por Timeframe</h2>
      <table class="dashboard__table">
        <thead>
          <tr>
            <th>Timeframe</th>
            <th>Trades</th>
            <th>Win Rate</th>
            <th>P&L</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in performanceStore.data.by_timeframe" :key="t.timeframe">
            <td>{{ t.timeframe }}</td>
            <td>{{ t.total_trades }}</td>
            <td>{{ t.win_rate_pct.toFixed(1) }}%</td>
            <td :class="t.total_pnl_usdt >= 0 ? 'text-success' : 'text-danger'">
              {{ formatCurrency(t.total_pnl_usdt) }}
            </td>
          </tr>
          <tr v-if="!performanceStore.data.by_timeframe.length">
            <td colspan="4" class="text-muted">Nenhum dado disponível</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.dashboard {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.dashboard__title {
  font-size: 28px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 24px;
}

.dashboard__metrics {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 32px;
}

.dashboard__section {
  margin-bottom: 32px;
}

.dashboard__subtitle {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 12px;
}

.dashboard__table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.dashboard__table th,
.dashboard__table td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid var(--color-border);
}

.dashboard__table th {
  background: var(--color-primary);
  color: #fff;
  font-weight: 600;
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.dashboard__table td {
  font-size: 14px;
  color: var(--color-text);
}

.text-success {
  color: var(--color-success);
  font-weight: 600;
}

.text-danger {
  color: var(--color-danger);
  font-weight: 600;
}

.text-muted {
  color: #999;
  font-style: italic;
}
</style>
