import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import Footer from '../Footer.vue';

describe('Footer', () => {
  it('renderiza versão padrão quando nenhuma prop fornecida', () => {
    const wrapper = mount(Footer);
    expect(wrapper.text()).toContain('Phicube v1.0.0');
  });

  it('renderiza versão personalizada via prop', () => {
    const wrapper = mount(Footer, {
      props: { botVersion: '2.5.0' },
    });
    expect(wrapper.text()).toContain('Phicube v2.5.0');
  });

  it('exibe status healthy/Online', () => {
    const wrapper = mount(Footer);
    expect(wrapper.text()).toContain('Online');
    expect(wrapper.find('.footer__status--healthy').exists()).toBe(true);
  });

  it('exibe copyright com ano atual', () => {
    const wrapper = mount(Footer);
    const currentYear = new Date().getFullYear();
    expect(wrapper.text()).toContain(String(currentYear));
    expect(wrapper.text()).toContain('Phicube Trading System');
  });
});
