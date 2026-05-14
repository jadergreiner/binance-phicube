<script setup lang="ts">
/**
 * NotFoundView — Página 404
 *
 * Exibida quando o usuário tenta acessar uma rota inexistente.
 */
import { useRouter } from 'vue-router';

const router = useRouter();

function goHome() {
  router.push('/');
}
</script>

<template>
  <div class="not-found">
    <div class="not-found__content">
      <h1 class="not-found__code">404</h1>
      <p class="not-found__message">Página não encontrada</p>
      <p class="not-found__description">A rota que você tentou acessar não existe ou foi movida.</p>
      <button class="not-found__button" @click="goHome">Voltar ao Dashboard</button>
    </div>
  </div>
</template>

<style scoped>
.not-found {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
  padding: 24px;
}

.not-found__content {
  text-align: center;
}

.not-found__code {
  font-size: 96px;
  font-weight: 700;
  color: var(--color-primary);
  margin: 0 0 8px;
  line-height: 1;
}

.not-found__message {
  font-size: 24px;
  color: var(--color-text);
  margin: 0 0 16px;
}

.not-found__description {
  font-size: 14px;
  color: #666;
  margin: 0 0 32px;
}

.not-found__button {
  padding: 12px 24px;
  background: var(--color-secondary);
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 15px;
  font-weight: 500;
  transition: background 0.2s;
}

.not-found__button:hover {
  background: #2980b9;
}
</style>
