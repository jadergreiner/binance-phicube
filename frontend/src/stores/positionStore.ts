/**
 * positionStore — Gerenciamento de estado das posições
 *
 * Store Pinia para posições abertas. Gerencia fetch, atualização
 * e computação de métricas (totalPnl, winCount, lossCount).
 */
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { getPositions } from '@/services/api';
import type { Position } from '@/services/types';

export const usePositionStore = defineStore('positions', () => {
  // State
  const positions = ref<Position[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const lastUpdate = ref<Date | null>(null);

  // Computed
  const totalPnl = computed(() => positions.value.reduce((sum, p) => sum + p.pnl_usdt, 0));

  const winCount = computed(() => positions.value.filter((p) => p.pnl_usdt > 0).length);

  const lossCount = computed(() => positions.value.filter((p) => p.pnl_usdt < 0).length);

  const totalPositions = computed(() => positions.value.length);

  // Actions
  async function fetchPositions() {
    loading.value = true;
    error.value = null;
    try {
      positions.value = await getPositions();
      lastUpdate.value = new Date();
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Erro ao carregar posições';
      error.value = message;
    } finally {
      loading.value = false;
    }
  }

  function updatePosition(updated: Position) {
    const index = positions.value.findIndex((p) => p.symbol === updated.symbol);
    if (index !== -1) {
      positions.value[index] = updated;
    }
  }

  function clearPositions() {
    positions.value = [];
    lastUpdate.value = null;
  }

  return {
    positions,
    loading,
    error,
    lastUpdate,
    totalPnl,
    winCount,
    lossCount,
    totalPositions,
    fetchPositions,
    updatePosition,
    clearPositions,
  };
});
