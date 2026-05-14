<script setup lang="ts">
/**
 * LoadingSpinner — Indicador de carregamento animado
 *
 * Spinner CSS-only com tamanhos small, medium, large.
 */

interface LoadingSpinnerProps {
  size?: 'small' | 'medium' | 'large';
}

withDefaults(defineProps<LoadingSpinnerProps>(), {
  size: 'medium',
});
</script>

<template>
  <div class="loading-spinner" :class="`loading-spinner--${size}`">
    <div class="loading-spinner__ring"></div>
  </div>
</template>

<style scoped>
.loading-spinner {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 24px;
}

.loading-spinner__ring {
  border-radius: 50%;
  border: 3px solid rgba(0, 0, 0, 0.1);
  border-top-color: var(--color-secondary);
  animation: spin 1s linear infinite;
}

.loading-spinner--small .loading-spinner__ring {
  width: 20px;
  height: 20px;
  border-width: 2px;
}

.loading-spinner--medium .loading-spinner__ring {
  width: 36px;
  height: 36px;
  border-width: 3px;
}

.loading-spinner--large .loading-spinner__ring {
  width: 52px;
  height: 52px;
  border-width: 4px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
