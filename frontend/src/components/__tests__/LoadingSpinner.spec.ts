import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import LoadingSpinner from '../LoadingSpinner.vue';

describe('LoadingSpinner', () => {
  it('renderiza com tamanho medium por padrão', () => {
    const wrapper = mount(LoadingSpinner);
    expect(wrapper.classes()).toContain('loading-spinner--medium');
  });

  it('renderiza com tamanho small', () => {
    const wrapper = mount(LoadingSpinner, {
      props: { size: 'small' },
    });
    expect(wrapper.classes()).toContain('loading-spinner--small');
  });

  it('renderiza com tamanho large', () => {
    const wrapper = mount(LoadingSpinner, {
      props: { size: 'large' },
    });
    expect(wrapper.classes()).toContain('loading-spinner--large');
  });

  it('contém o elemento ring animado', () => {
    const wrapper = mount(LoadingSpinner);
    expect(wrapper.find('.loading-spinner__ring').exists()).toBe(true);
  });
});
