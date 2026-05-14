import { describe, it, expect, beforeEach, vi } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { usePerformanceStore } from '../performanceStore';
import type { PerformanceResponse } from '@/services/types';

vi.mock('@/services/api', () => ({
  getPerformance: vi.fn(),
}));

import { getPerformance } from '@/services/api';

const mockResponse: PerformanceResponse = {
  global: {
    total_trades: 100,
    win_rate_pct: 65,
    total_pnl_usdt: 5000,
    avg_rrr: 2.5,
    max_drawdown_usdt: 1000,
    profit_factor: 3.2,
  },
  by_symbol: [
    {
      symbol: 'BTCUSDT',
      total_trades: 50,
      win_rate_pct: 70,
      total_pnl_usdt: 3000,
      avg_rrr: 2.8,
      max_drawdown_usdt: 500,
      profit_factor: 3.5,
    },
  ],
  by_timeframe: [
    {
      timeframe: '15m',
      total_trades: 80,
      win_rate_pct: 62,
      total_pnl_usdt: 4000,
      avg_rrr: 2.3,
      max_drawdown_usdt: 800,
      profit_factor: 3.0,
    },
  ],
};

describe('performanceStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it('fetchPerformance atualiza state', async () => {
    (getPerformance as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse);

    const store = usePerformanceStore();
    expect(store.loading).toBe(false);

    const promise = store.fetchPerformance();
    expect(store.loading).toBe(true);

    await promise;

    expect(store.loading).toBe(false);
    expect(store.data).toEqual(mockResponse);
    expect(store.error).toBeNull();
  });

  it('fetchPerformance trata erro', async () => {
    (getPerformance as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Erro na API'));

    const store = usePerformanceStore();
    await store.fetchPerformance();

    expect(store.loading).toBe(false);
    expect(store.data).toBeNull();
    expect(store.error).toBe('Erro na API');
  });

  it('globalMetrics retorna dados globais', () => {
    const store = usePerformanceStore();
    store.$patch({ data: mockResponse });

    expect(store.globalMetrics).toEqual(mockResponse.global);
    expect(store.globalMetrics?.total_trades).toBe(100);
    expect(store.globalMetrics?.win_rate_pct).toBe(65);
  });

  it('globalMetrics retorna null se data é null', () => {
    const store = usePerformanceStore();
    expect(store.globalMetrics).toBeNull();
  });
});
