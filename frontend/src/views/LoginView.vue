<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { authStore } from '@/stores/authStore';

const router = useRouter();
const route = useRoute();

const isLoading = ref(false);
const error = ref<string | null>(null);
const fallbackMode = ref(false);
const fallbackUsername = ref('');
const fallbackPassword = ref('');

onMounted(() => {
  // Verificar se há código de callback na URL
  const urlParams = new URLSearchParams(window.location.search);
  const code = urlParams.get('code');
  const state = urlParams.get('state');

  if (code) {
    handleCallback(code, state);
  }
});

async function handleCallback(code: string, state: string | null) {
  isLoading.value = true;
  error.value = null;

  try {
    await authStore.handleCallback(code, state);
    const redirect = (route.query.redirect as string) || '/';
    router.push(redirect);
  } catch (e) {
    error.value = 'Falha na autenticação. Tente novamente.';
  } finally {
    isLoading.value = false;
  }
}

async function loginWithGoogle() {
  isLoading.value = true;
  error.value = null;

  try {
    await authStore.loginWithGoogle();
  } catch (e) {
    error.value = 'Falha ao redirecionar para Google.';
    isLoading.value = false;
  }
}

async function loginWithFallback() {
  if (!fallbackUsername.value || !fallbackPassword.value) {
    error.value = 'Preencha usuário e senha.';
    return;
  }

  isLoading.value = true;
  error.value = null;

  try {
    await authStore.loginWithFallback(fallbackUsername.value, fallbackPassword.value);
    const redirect = (route.query.redirect as string) || '/';
    router.push(redirect);
  } catch (e) {
    error.value = 'Credenciais inválidas.';
  } finally {
    isLoading.value = false;
  }
}
</script>

<template>
  <div class="login-container">
    <div class="login-card">
      <h1 class="login-title">Phicube Dashboard</h1>
      <p class="login-subtitle">Autenticação necessária</p>

      <!-- Modo OAuth -->
      <div v-if="!fallbackMode">
        <button class="btn-google" @click="loginWithGoogle" :disabled="isLoading">
          <svg class="google-icon" viewBox="0 0 24 24">
            <path
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              fill="#4285F4"
            />
            <path
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              fill="#34A853"
            />
            <path
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              fill="#FBBC05"
            />
            <path
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              fill="#EA4335"
            />
          </svg>
          Entrar com Google
        </button>

        <button class="btn-fallback" @click="fallbackMode = true">Usar login de emergência</button>
      </div>

      <!-- Modo Fallback -->
      <div v-else class="fallback-form">
        <div class="form-group">
          <label for="username">Usuário</label>
          <input
            id="username"
            v-model="fallbackUsername"
            type="text"
            placeholder="Usuário de emergência"
          />
        </div>

        <div class="form-group">
          <label for="password">Senha</label>
          <input
            id="password"
            v-model="fallbackPassword"
            type="password"
            placeholder="Senha de emergência"
          />
        </div>

        <button class="btn-login" @click="loginWithFallback" :disabled="isLoading">Entrar</button>

        <button class="btn-back" @click="fallbackMode = false">Voltar</button>
      </div>

      <!-- Error message -->
      <div v-if="error" class="error-message">
        {{ error }}
      </div>

      <!-- Loading -->
      <div v-if="isLoading" class="loading">
        <div class="spinner"></div>
        <span>Autenticando...</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
}

.login-card {
  background: #0f0f1a;
  padding: 2.5rem;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  width: 100%;
  max-width: 400px;
  text-align: center;
}

.login-title {
  color: #fff;
  font-size: 1.75rem;
  margin-bottom: 0.5rem;
}

.login-subtitle {
  color: #888;
  margin-bottom: 2rem;
}

.btn-google {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  width: 100%;
  padding: 0.875rem;
  background: #fff;
  color: #333;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition:
    transform 0.2s,
    box-shadow 0.2s;
}

.btn-google:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(255, 255, 255, 0.2);
}

.btn-google:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.google-icon {
  width: 20px;
  height: 20px;
}

.btn-fallback {
  margin-top: 1rem;
  background: transparent;
  color: #666;
  border: none;
  font-size: 0.875rem;
  cursor: pointer;
  text-decoration: underline;
}

.btn-fallback:hover {
  color: #888;
}

.fallback-form {
  text-align: left;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  color: #aaa;
  font-size: 0.875rem;
  margin-bottom: 0.5rem;
}

.form-group input {
  width: 100%;
  padding: 0.75rem;
  background: #1a1a2e;
  border: 1px solid #333;
  border-radius: 8px;
  color: #fff;
  font-size: 1rem;
}

.form-group input:focus {
  outline: none;
  border-color: #4285f4;
}

.btn-login {
  width: 100%;
  padding: 0.875rem;
  background: #4285f4;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  margin-top: 1rem;
}

.btn-login:hover:not(:disabled) {
  background: #3367d6;
}

.btn-login:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-back {
  display: block;
  width: 100%;
  margin-top: 0.75rem;
  background: transparent;
  color: #666;
  border: none;
  font-size: 0.875rem;
  cursor: pointer;
}

.error-message {
  margin-top: 1rem;
  padding: 0.75rem;
  background: rgba(234, 67, 53, 0.1);
  border: 1px solid #ea4335;
  border-radius: 8px;
  color: #ea4335;
  font-size: 0.875rem;
}

.loading {
  margin-top: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  color: #888;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid #333;
  border-top-color: #4285f4;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
