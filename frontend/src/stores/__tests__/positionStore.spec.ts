import { describe, it, expect, beforeEach, vi } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { usePositionStore } from '../positionStore';
import type { Position } from '@/services/types';

vi.mock('@/services/api', () => ({
  getPositions: vi.fn(),
}));

import { getPositions } from '@/services/api';

const mockPositions: Position[] = [
  {
    symbol: 'BTCUSDT',
    direction: 'LONG',
    entry_price: 50000,
    current_price: 51000,
    quantity: 0.5,
    pnl_usdt: 500,
    pnl_pct: 2.0,
    sl_price: 49000,
    tp_price: 52000,
    open_time: '2024-01-01T00:00:00Z',
    leverage: 5,
    margin_usdt: 5000,
  },
  {
    symbol: 'ETHUSDT',
    direction: 'SHORT',
    entry_price: 3000,
    current_price: 2900,
    quantity: 2.0,
    pnl_usdt: 200,
    pnl_pct: 3.3,
    sl_price: 3100,
    tp_price: 2800,
    open_time: '2024-01-01T00:00:00Z',
    leverage: 5,
    margin_usdt: 1200,
  },
  {
    symbol: 'SOLUSDT',
    direction: 'LONG',
    entry_price: 100,
    current_price: 95,
    quantity: 10,
    pnl_usdt: -50,
    pnl_pct: -5.0,
    sl_price: 90,
    tp_price: 110,
    open_time: '2024-01-01T00:00:00Z',
    leverage: 3,
    margin_usdt: 333,
  },
];

describe('positionStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it('fetchPositions atualiza state corretamente', async () => {
    (getPositions as ReturnType<typeof vi.fn>).mockResolvedValue(mockPositions);

    const store = usePositionStore();
    expect(store.loading).toBe(false);
    expect(store.positions).toEqual([]);

    const promise = store.fetchPositions();
    expect(store.loading).toBe(true);

    await promise;

    expect(store.loading).toBe(false);
    expect(store.positions).toEqual(mockPositions);
    expect(store.error).toBeNull();
    expect(store.lastUpdate).toBeInstanceOf(Date);
  });

  it('fetchPositions trata erro corretamente', async () => {
    (getPositions as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('API Error'));

    const store = usePositionStore();
    await store.fetchPositions();

    expect(store.loading).toBe(false);
    expect(store.positions).toEqual([]);
    expect(store.error).toBe('API Error');
  });

  it('totalPnl computa soma correta', () => {
    const store = usePositionStore();
    store.$patch({ positions: mockPositions });

    expect(store.totalPnl).toBe(500 + 200 + -50);
  });

  it('winCount conta posições com PnL positivo', () => {
    const store = usePositionStore();
    store.$patch({ positions: mockPositions });

    expect(store.winCount).toBe(2);
  });

  it('lossCount conta posições com PnL negativo', () => {
    const store = usePositionStore();
    store.$patch({ positions: mockPositions });

    expect(store.lossCount).toBe(1);
  });

  it('updatePosition modifica posição existente', () => {
    const store = usePositionStore();
    store.$patch({ positions: mockPositions });

    const updated: Position = { ...mockPositions[0], current_price: 52000, pnl_usdt: 1000 };
    store.updatePosition(updated);

    const btcPosition = store.positions.find((p) => p.symbol === 'BTCUSDT');
    expect(btcPosition?.current_price).toBe(52000);
    expect(btcPosition?.pnl_usdt).toBe(1000);
  });

  it('clearPositions limpa lista', () => {
    const store = usePositionStore();
    store.$patch({ positions: mockPositions, lastUpdate: new Date() });

    store.clearPositions();

    expect(store.positions).toEqual([]);
    expect(store.lastUpdate).toBeNull();
  });
});
