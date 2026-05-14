<script setup lang="ts">
/**
 * App.vue — Componente raiz da aplicação
 *
 * Inclui Navbar, router-view e Footer em layout flex.
 */
import Navbar from '@/components/Layout/Navbar.vue';
import Footer from '@/components/Layout/Footer.vue';
</script>

<template>
  <div class="app">
    <Navbar />
    <main class="app__main">
      <router-view />
    </main>
    <Footer bot-version="1.0.0" />
  </div>
</template>

<style>
@import '@/styles/main.css';
@import '@/styles/components.css';

.app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.app__main {
  flex: 1;
  background: var(--color-bg);
}
</style>
