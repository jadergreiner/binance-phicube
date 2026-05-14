<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { authStore } from '@/stores/authStore';

const router = useRouter();

let unsubscribe: (() => void) | null = null;

onMounted(() => {
  // Escuta evento de token expirado e redireciona para login
  unsubscribe = authStore.onTokenExpired(() => {
    authStore.logout();
    router.push('/login');
  });
});

onUnmounted(() => {
  if (unsubscribe) {
    unsubscribe();
  }
});
</script>

<template>
  <!-- Componente invisível que apenas observa eventos de auth -->
  <div v-if="false"></div>
</template>