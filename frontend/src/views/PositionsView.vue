<script setup lang="ts">
/**
 * PositionsView — Tela de posições abertas
 *
 * Exibe tabela com todas as posições abertas no momento.
 * Atualiza automaticamente a cada 60 segundos.
 */
import { onMounted, onUnmounted } from 'vue';
import { usePositionStore } from '@/stores/positionStore';
import PositionTable from '@/components/PositionTable.vue';
import LoadingSpinner from '@/components/LoadingSpinner.vue';
import ErrorBanner from '@/components/ErrorBanner.vue';

const positionStore = usePositionStore();
let pollingInterval: ReturnType<typeof setInterval> | null = null;

onMounted(async () => {
  await positionStore.fetchPositions();
  pollingInterval = setInterval(() => {
    positionStore.fetchPositions();
  }, 60000);
});

onUnmounted(() => {
  if (pollingInterval) clearInterval(pollingInterval);
});
</script>

<template>
  <div class="positions">
    <h1 class="positions__title">Posições Abertas</h1>

    <ErrorBanner
      v-if="positionStore.error"
      :message="positionStore.error"
      type="error"
      @close="positionStore.error = null"
    />

    <LoadingSpinner v-if="positionStore.loading" size="large" />

    <PositionTable v-else :positions="positionStore.positions" :loading="positionStore.loading" />
  </div>
</template>

<style scoped>
.positions {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.positions__title {
  font-size: 28px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 24px;
}
</style>
