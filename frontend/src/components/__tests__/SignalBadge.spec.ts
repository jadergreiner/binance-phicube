import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import SignalBadge from '../SignalBadge.vue';

describe('SignalBadge', () => {
  it('renderiza LONG com classe long', () => {
    const wrapper = mount(SignalBadge, {
      props: { direction: 'LONG' },
    });
    expect(wrapper.text()).toBe('LONG');
    expect(wrapper.classes()).toContain('signal-badge--long');
  });

  it('renderiza SHORT com classe short', () => {
    const wrapper = mount(SignalBadge, {
      props: { direction: 'SHORT' },
    });
    expect(wrapper.text()).toBe('SHORT');
    expect(wrapper.classes()).toContain('signal-badge--short');
  });

  it('renderiza NEUTRO com classe neutro', () => {
    const wrapper = mount(SignalBadge, {
      props: { direction: 'NEUTRO' },
    });
    expect(wrapper.text()).toBe('NEUTRO');
    expect(wrapper.classes()).toContain('signal-badge--neutro');
  });
});
