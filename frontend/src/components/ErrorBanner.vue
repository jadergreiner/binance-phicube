<script setup lang="ts">
/**
 * ErrorBanner — Banner de erro/warning/info
 *
 * Exibe mensagem com cores específicas e auto-desaparece após 5s.
 */
import { onMounted, ref } from 'vue';

interface ErrorBannerProps {
  message: string;
  type?: 'error' | 'warning' | 'info';
}

withDefaults(defineProps<ErrorBannerProps>(), {
  type: 'error',
});

const emit = defineEmits<{
  close: [];
}>();

const visible = ref(true);

onMounted(() => {
  setTimeout(() => {
    visible.value = false;
    emit('close');
  }, 5000);
});

function dismiss() {
  visible.value = false;
  emit('close');
}

const iconMap: Record<string, string> = {
  error: '✕',
  warning: '⚠',
  info: 'ℹ',
};
</script>

<template>
  <div v-if="visible" class="error-banner" :class="`error-banner--${type}`" role="alert">
    <span class="error-banner__icon">{{ iconMap[type] }}</span>
    <span class="error-banner__message">{{ message }}</span>
    <button class="error-banner__close" @click="dismiss" aria-label="Fechar">✕</button>
  </div>
</template>

<style scoped>
.error-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-radius: 6px;
  margin-bottom: 16px;
  font-size: 14px;
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.error-banner--error {
  background: rgba(231, 76, 60, 0.1);
  color: var(--color-danger);
  border: 1px solid rgba(231, 76, 60, 0.3);
}

.error-banner--warning {
  background: rgba(243, 156, 18, 0.1);
  color: var(--color-warning);
  border: 1px solid rgba(243, 156, 18, 0.3);
}

.error-banner--info {
  background: rgba(52, 152, 219, 0.1);
  color: var(--color-secondary);
  border: 1px solid rgba(52, 152, 219, 0.3);
}

.error-banner__icon {
  font-size: 16px;
  flex-shrink: 0;
}

.error-banner__message {
  flex: 1;
}

.error-banner__close {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  opacity: 0.6;
  padding: 4px;
  line-height: 1;
  color: inherit;
}

.error-banner__close:hover {
  opacity: 1;
}
</style>
