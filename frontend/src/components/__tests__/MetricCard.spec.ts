import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import MetricCard from '../MetricCard.vue';

describe('MetricCard', () => {
  it('renderiza label e valor', () => {
    const wrapper = mount(MetricCard, {
      props: { label: 'Total PnL', value: 500, unit: 'USDT' },
    });
    expect(wrapper.text()).toContain('Total PnL');
    expect(wrapper.text()).toContain('500');
    expect(wrapper.text()).toContain('USDT');
  });

  it('exibe delta com seta para cima quando positivo', () => {
    const wrapper = mount(MetricCard, {
      props: { label: 'Win Rate', value: '75%', delta: 2.5, unit: '%' },
    });
    expect(wrapper.text()).toContain('↑');
    expect(wrapper.text()).toContain('+2.5%');
    expect(wrapper.find('.delta--positive').exists()).toBe(true);
  });

  it('exibe delta com seta para baixo quando negativo', () => {
    const wrapper = mount(MetricCard, {
      props: { label: 'Drawdown', value: '1000', delta: -3.2, unit: 'USDT' },
    });
    expect(wrapper.text()).toContain('↓');
    expect(wrapper.text()).toContain('-3.2USDT');
    expect(wrapper.find('.delta--negative').exists()).toBe(true);
  });

  it('não exibe delta se não fornecido', () => {
    const wrapper = mount(MetricCard, {
      props: { label: 'Total Trades', value: 42 },
    });
    expect(wrapper.find('.metric-card__delta').exists()).toBe(false);
  });
});
