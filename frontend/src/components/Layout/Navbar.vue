<script setup lang="ts">
/**
 * Navbar — Barra de navegação superior
 *
 * Exibe logo e links de navegação para todas as views.
 */
</script>

<template>
  <nav class="navbar">
    <div class="navbar__container">
      <router-link to="/" class="navbar__logo"> Phicube Dashboard </router-link>

      <div class="navbar__links">
        <router-link to="/" class="navbar__link" exact-active-class="navbar__link--active">
          Dashboard
        </router-link>
        <router-link to="/positions" class="navbar__link" active-class="navbar__link--active">
          Posições
        </router-link>
        <router-link to="/history" class="navbar__link" active-class="navbar__link--active">
          Histórico
        </router-link>
        <router-link to="/settings" class="navbar__link" active-class="navbar__link--active">
          Configuração
        </router-link>
      </div>
    </div>
  </nav>
</template>

<style scoped>
.navbar {
  background: var(--color-primary);
  color: #fff;
  padding: 0 24px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.navbar__container {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 1200px;
  margin: 0 auto;
  height: 56px;
}

.navbar__logo {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  text-decoration: none;
  letter-spacing: 0.5px;
}

.navbar__links {
  display: flex;
  gap: 4px;
}

.navbar__link {
  color: rgba(255, 255, 255, 0.8);
  text-decoration: none;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
}

.navbar__link:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
}

.navbar__link--active {
  color: #fff;
  background: rgba(255, 255, 255, 0.15);
  font-weight: 600;
}

@media (max-width: 640px) {
  .navbar__container {
    flex-direction: column;
    height: auto;
    padding: 12px 0;
    gap: 8px;
  }

  .navbar__links {
    flex-wrap: wrap;
    justify-content: center;
  }
}
</style>
