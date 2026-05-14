<script setup lang="ts">
/**
 * Footer — Rodapé do sistema
 *
 * Exibe versão do bot, status e copyright.
 */
const currentYear = new Date().getFullYear();
const statusClass = 'healthy';
const statusText = 'Online';

defineProps<{
  botVersion?: string;
}>();
</script>

<template>
  <footer class="footer">
    <div class="footer__container">
      <div class="footer__info">
        <span class="footer__version">Phicube v{{ botVersion || '1.0.0' }}</span>
        <span class="footer__status" :class="`footer__status--${statusClass}`">
          {{ statusText }}
        </span>
      </div>
      <div class="footer__copyright">&copy; {{ currentYear }} Phicube Trading System</div>
    </div>
  </footer>
</template>

<style scoped>
.footer {
  background: var(--color-primary);
  color: rgba(255, 255, 255, 0.7);
  padding: 16px 24px;
  margin-top: auto;
  font-size: 12px;
}

.footer__container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 1200px;
  margin: 0 auto;
}

.footer__info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.footer__status {
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 600;
  font-size: 11px;
  text-transform: uppercase;
}

.footer__status--healthy {
  background: rgba(39, 174, 96, 0.2);
  color: var(--color-success);
}

.footer__status--degraded {
  background: rgba(243, 156, 18, 0.2);
  color: var(--color-warning);
}

.footer__status--unhealthy {
  background: rgba(231, 76, 60, 0.2);
  color: var(--color-danger);
}

@media (max-width: 640px) {
  .footer__container {
    flex-direction: column;
    gap: 8px;
    text-align: center;
  }
}
</style>
