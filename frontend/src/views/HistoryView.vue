<script setup lang="ts">
/**
 * HistoryView — Histórico de trades (mockado nesta versão)
 *
 * Será implementado com dados reais em SPEC_035 v2.1.
 */
</script>

<template>
  <div class="history">
    <h1 class="history__title">Histórico de Trades</h1>

    <div class="history__placeholder">
      <p class="history__message">Histórico indisponível nesta versão</p>
      <p class="history__note">Será implementado em SPEC_035 v2.1</p>
    </div>
  </div>
</template>

<style scoped>
.history {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
  text-align: center;
}

.history__title {
  font-size: 28px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 48px;
}

.history__placeholder {
  padding: 48px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.history__message {
  font-size: 18px;
  color: var(--color-text);
  margin-bottom: 8px;
}

.history__note {
  font-size: 14px;
  color: #999;
  font-style: italic;
}
</style>
