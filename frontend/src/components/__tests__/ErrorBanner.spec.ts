import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount } from '@vue/test-utils';
import ErrorBanner from '../ErrorBanner.vue';

describe('ErrorBanner', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renderiza mensagem de erro', () => {
    const wrapper = mount(ErrorBanner, {
      props: { message: 'Erro de conexão' },
    });
    expect(wrapper.text()).toContain('Erro de conexão');
    expect(wrapper.classes()).toContain('error-banner--error');
  });

  it('renderiza tipo warning', () => {
    const wrapper = mount(ErrorBanner, {
      props: { message: 'Aviso importante', type: 'warning' },
    });
    expect(wrapper.classes()).toContain('error-banner--warning');
    expect(wrapper.text()).toContain('⚠');
  });

  it('renderiza tipo info', () => {
    const wrapper = mount(ErrorBanner, {
      props: { message: 'Informação', type: 'info' },
    });
    expect(wrapper.classes()).toContain('error-banner--info');
    expect(wrapper.text()).toContain('ℹ');
  });

  it('emite close ao clicar no botão fechar', async () => {
    const wrapper = mount(ErrorBanner, {
      props: { message: 'Erro' },
    });
    await wrapper.find('button').trigger('click');
    expect(wrapper.emitted('close')).toBeTruthy();
    expect(wrapper.find('.error-banner').exists()).toBe(false);
  });

  it('auto-desaparece após 5 segundos', () => {
    mount(ErrorBanner, {
      props: { message: 'Erro' },
    });
    // After mount, setTimeout of 5000ms is set
    expect(vi.getTimerCount()).toBe(1);
  });

  it('emite close após 5 segundos (auto-dismiss)', () => {
    const wrapper = mount(ErrorBanner, {
      props: { message: 'Erro' },
    });
    vi.advanceTimersByTime(5000);
    expect(wrapper.emitted('close')).toBeTruthy();
  });
});
