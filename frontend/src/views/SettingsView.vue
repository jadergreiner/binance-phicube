<script setup lang="ts">
/**
 * SettingsView — Tela de configuração
 *
 * Exibe informações do sistema e status dos serviços.
 */
import { ref } from 'vue';
import { getHealth } from '@/services/api';
import type { HealthStatus } from '@/services/types';

const botVersion = import.meta.env.VITE_APP_VERSION || '1.0.0';
const appEnv = import.meta.env.VITE_APP_ENV || 'development';
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const healthStatus = ref<HealthStatus | null>(null);
const healthLoading = ref(false);

async function reloadStatus() {
  healthLoading.value = true;
  try {
    healthStatus.value = await getHealth();
  } catch {
    healthStatus.value = null;
  } finally {
    healthLoading.value = false;
  }
}
</script>

<template>
  <div class="settings">
    <h1 class="settings__title">Configuração</h1>

    <div class="settings__cards">
      <div class="settings__card">
        <h3 class="settings__card-title">Informações do Sistema</h3>
        <dl class="settings__list">
          <dt>Versão do Bot</dt>
          <dd>{{ botVersion }}</dd>
          <dt>Ambiente</dt>
          <dd>{{ appEnv }}</dd>
          <dt>API Base URL</dt>
          <dd>
            <code>{{ apiBaseUrl }}</code>
          </dd>
        </dl>
      </div>

      <div class="settings__card">
        <h3 class="settings__card-title">Status dos Serviços</h3>
        <dl class="settings__list">
          <dt>MongoDB</dt>
          <dd
            v-if="healthStatus"
            :class="healthStatus.mongodb_connected ? 'status-ok' : 'status-error'"
          >
            {{ healthStatus.mongodb_connected ? 'Conectado' : 'Desconectado' }}
          </dd>
          <dd v-else class="status-pending">—</dd>

          <dt>Binance</dt>
          <dd
            v-if="healthStatus"
            :class="healthStatus.binance_client_ok ? 'status-ok' : 'status-error'"
          >
            {{ healthStatus.binance_client_ok ? 'Online' : 'Offline' }}
          </dd>
          <dd v-else class="status-pending">—</dd>

          <dt>Uptime</dt>
          <dd>{{ healthStatus ? `${Math.floor(healthStatus.uptime_seconds / 60)} min` : '—' }}</dd>
        </dl>

        <button class="settings__button" :disabled="healthLoading" @click="reloadStatus">
          {{ healthLoading ? 'Carregando...' : 'Recarregar Status' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings {
  padding: 24px;
  max-width: 800px;
  margin: 0 auto;
}

.settings__title {
  font-size: 28px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 24px;
}

.settings__cards {
  display: grid;
  gap: 24px;
}

.settings__card {
  background: #fff;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.settings__card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--color-border);
}

.settings__list {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 8px 16px;
  margin-bottom: 16px;
}

.settings__list dt {
  font-size: 13px;
  color: #666;
  font-weight: 500;
}

.settings__list dd {
  font-size: 14px;
  color: var(--color-text);
  margin: 0;
}

.settings__list code {
  font-size: 13px;
  background: var(--color-bg);
  padding: 2px 6px;
  border-radius: 4px;
}

.status-ok {
  color: var(--color-success);
  font-weight: 600;
}

.status-error {
  color: var(--color-danger);
  font-weight: 600;
}

.status-pending {
  color: #999;
}

.settings__button {
  padding: 8px 16px;
  background: var(--color-secondary);
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
}

.settings__button:hover:not(:disabled) {
  background: #2980b9;
}

.settings__button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
