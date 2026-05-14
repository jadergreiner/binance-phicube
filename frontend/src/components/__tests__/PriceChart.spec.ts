import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import PriceChart from '../PriceChart.vue';

describe('PriceChart', () => {
  it('exibe placeholder em desenvolvimento por padrão', () => {
    const wrapper = mount(PriceChart, {
      props: { loading: false },
    });
    expect(wrapper.text()).toContain('Gráfico de preço em desenvolvimento');
    expect(wrapper.text()).toContain('SPEC_039');
  });

  it('exibe mensagem de carregando quando loading=true', () => {
    const wrapper = mount(PriceChart, {
      props: { loading: true },
    });
    expect(wrapper.text()).toContain('Carregando gráfico...');
  });

  it('renderiza com arrays vazios por padrão', () => {
    const wrapper = mount(PriceChart, {
      props: { loading: false },
    });
    expect(wrapper.find('.price-chart').exists()).toBe(true);
  });
});
