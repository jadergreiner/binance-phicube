/**
 * setup.ts — Configuração global de testes
 *
 * Define mocks globais para o ambiente Vitest + jsdom.
 */
import { vi } from 'vitest';

// Define VITE_ environment variables for import.meta.env in tests
process.env.VITE_API_BASE_URL = '/api/v1';
process.env.VITE_APP_ENV = 'test';

// Mock window.matchMedia (necessário para alguns componentes)
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});
