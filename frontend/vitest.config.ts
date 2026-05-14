import { defineConfig } from 'vitest/config';
import vue from '@vitejs/plugin-vue';
import { resolve } from 'path';

export default defineConfig({
  plugins: [vue()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
    include: ['src/**/*.spec.ts', 'src/**/__tests__/**/*.spec.ts'],
    env: {
      VITE_API_BASE_URL: '/api/v1',
      VITE_APP_ENV: 'test',
    },
    coverage: {
      provider: 'v8',
      lines: 70,
      functions: 70,
      branches: 70,
      statements: 70,
      include: ['src/components/**/*.{vue,ts}', 'src/stores/**/*.ts', 'src/services/**/*.ts'],
    },
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
});
