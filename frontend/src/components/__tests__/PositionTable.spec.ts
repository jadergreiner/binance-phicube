import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import PositionTable from '../PositionTable.vue';
import type { Position } from '@/services/types';

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

describe('PositionTable', () => {
  it('renderiza lista de posições', () => {
    const wrapper = mount(PositionTable, {
      props: { positions: mockPositions, loading: false },
    });
    expect(wrapper.text()).toContain('BTCUSDT');
    expect(wrapper.text()).toContain('ETHUSDT');
    expect(wrapper.text()).toContain('SOLUSDT');
  });

  it('exibe spinner quando loading=true', () => {
    const wrapper = mount(PositionTable, {
      props: { positions: [], loading: true },
    });
    // LoadingSpinner component should be present
    expect(wrapper.findComponent({ name: 'LoadingSpinner' }).exists()).toBe(true);
  });

  it('exibe mensagem vazia quando não há posições', () => {
    const wrapper = mount(PositionTable, {
      props: { positions: [], loading: false },
    });
    expect(wrapper.text()).toContain('Nenhuma posição aberta');
  });

  it('filtra por símbolo', async () => {
    const wrapper = mount(PositionTable, {
      props: { positions: mockPositions, loading: false },
    });
    const input = wrapper.find('input');
    await input.setValue('BTC');
    // After filtering, only BTCUSDT should be visible in table rows
    const rows = wrapper.findAll('tbody tr');
    expect(rows.length).toBe(1);
    expect(rows[0].text()).toContain('BTCUSDT');
  });

  it('emite evento sort ao clicar no header', async () => {
    const wrapper = mount(PositionTable, {
      props: { positions: mockPositions, loading: false },
    });
    const header = wrapper.findAll('th.clickable')[0]; // symbol column
    await header.trigger('click');
    expect(wrapper.emitted('sort')).toBeTruthy();
    expect(wrapper.emitted('sort')![0]).toEqual(['symbol', 'asc']);
  });

  it('alterna direção de ordenação no segundo clique', async () => {
    const wrapper = mount(PositionTable, {
      props: { positions: mockPositions, loading: false },
    });
    const header = wrapper.findAll('th.clickable')[0];
    await header.trigger('click');
    await header.trigger('click');
    expect(wrapper.emitted('sort')![1]).toEqual(['symbol', 'desc']);
  });

  it('exibe PnL positivo em verde e negativo em vermelho', () => {
    const wrapper = mount(PositionTable, {
      props: { positions: mockPositions, loading: false },
    });
    const pnlCells = wrapper.findAll('td:nth-child(6)'); // PnL USDT column
    // BTCUSDT: +500 (positive)
    expect(pnlCells[0].classes()).toContain('pnl-positive');
    // SOLUSDT: -50 (negative)
    expect(pnlCells[2].classes()).toContain('pnl-negative');
  });
});
