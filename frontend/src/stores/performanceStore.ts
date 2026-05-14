/**
 * performanceStore — Gerenciamento de estado de performance
 *
 * Store Pinia para métricas de performance. Gerencia fetch de
 * dados globais, por símbolo e por timeframe.
 */
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { getPerformance } from '@/services/api';
import type { PerformanceResponse, PerformanceGlobal } from '@/services/types';

export const usePerformanceStore = defineStore('performance', () => {
  // State
  const data = ref<PerformanceResponse | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const lastUpdate = ref<Date | null>(null);

  // Computed
  const globalMetrics = computed<PerformanceGlobal | null>(() => data.value?.global ?? null);

  // Actions
  async function fetchPerformance() {
    loading.value = true;
    error.value = null;
    try {
      data.value = await getPerformance();
      lastUpdate.value = new Date();
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Erro ao carregar performance';
      error.value = message;
    } finally {
      loading.value = false;
    }
  }

  function clearPerformance() {
    data.value = null;
    lastUpdate.value = null;
  }

  return {
    data,
    loading,
    error,
    lastUpdate,
    globalMetrics,
    fetchPerformance,
    clearPerformance,
  };
});
