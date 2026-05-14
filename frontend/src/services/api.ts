/**
 * API Service — Wrapper axios para API Phicube
 *
 * Inclui retry com backoff exponencial, tratamento de erro 401
 * e funções tipadas para cada endpoint.
 */
import axios from 'axios';
import type { AxiosInstance, AxiosError, AxiosRequestConfig } from 'axios';
import { API_BASE_URL, REQUEST_TIMEOUT, MAX_RETRIES } from './config';
import type { Position, PerformanceResponse, HealthStatus, ApiError } from './types';

// Cria instância axios com configuração base
const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: REQUEST_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor de resposta com retry e backoff exponencial
let retryCount = 0;

api.interceptors.response.use(
  (response) => {
    retryCount = 0;
    return response;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

    // Tratamento 401 — dispara evento customizado
    if (error.response?.status === 401) {
      window.dispatchEvent(new CustomEvent('auth:unauthorized'));
      return Promise.reject(error);
    }

    // Retry com backoff exponencial para erros de rede/5xx
    if (
      (!error.response || error.response.status >= 500) &&
      retryCount < MAX_RETRIES &&
      !originalRequest._retry
    ) {
      retryCount++;
      const delay = Math.pow(2, retryCount) * 1000;
      await new Promise((resolve) => setTimeout(resolve, delay));
      return api(originalRequest);
    }

    retryCount = 0;
    return Promise.reject(error);
  }
);

/**
 * Parseia erro genérico para ApiError
 */
export function parseApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ message?: string }>;
    return {
      status: axiosError.response?.status ?? 0,
      message: axiosError.response?.data?.message ?? axiosError.message,
      timestamp: new Date().toISOString(),
    };
  }
  return {
    status: 0,
    message: error instanceof Error ? error.message : 'Erro desconhecido',
    timestamp: new Date().toISOString(),
  };
}

/**
 * GET /positions — Retorna lista de posições abertas
 */
export async function getPositions(): Promise<Position[]> {
  const response = await api.get<Position[]>('/positions');
  return response.data;
}

/**
 * GET /performance — Retorna métricas de performance
 */
export async function getPerformance(): Promise<PerformanceResponse> {
  const response = await api.get<PerformanceResponse>('/performance');
  return response.data;
}

/**
 * GET /health — Retorna status de saúde do sistema
 */
export async function getHealth(): Promise<HealthStatus> {
  const response = await api.get<HealthStatus>('/health');
  return response.data;
}

export default api;
