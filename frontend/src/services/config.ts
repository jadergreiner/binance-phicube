/**
 * Configuração da API
 *
 * Valores lidos de variáveis de ambiente com fallback.
 */

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';
export const REQUEST_TIMEOUT = 10000;
export const MAX_RETRIES = 3;
