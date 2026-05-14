import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import Navbar from '../Navbar.vue';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'Dashboard', component: { template: '<div>Dashboard</div>' } },
    { path: '/positions', name: 'Positions', component: { template: '<div>Positions</div>' } },
    { path: '/history', name: 'History', component: { template: '<div>History</div>' } },
    { path: '/settings', name: 'Settings', component: { template: '<div>Settings</div>' } },
  ],
});

describe('Navbar', () => {
  it('renderiza o título Phicube Dashboard', async () => {
    router.push('/');
    await router.isReady();
    const wrapper = mount(Navbar, {
      global: { plugins: [router] },
    });
    expect(wrapper.text()).toContain('Phicube Dashboard');
  });

  it('contém links de navegação para todas as views', async () => {
    router.push('/');
    await router.isReady();
    const wrapper = mount(Navbar, {
      global: { plugins: [router] },
    });
    expect(wrapper.text()).toContain('Dashboard');
    expect(wrapper.text()).toContain('Posições');
    expect(wrapper.text()).toContain('Histórico');
    expect(wrapper.text()).toContain('Configuração');
  });

  it('contém 4 router-links de navegação', async () => {
    router.push('/');
    await router.isReady();
    const wrapper = mount(Navbar, {
      global: { plugins: [router] },
    });
    const links = wrapper.findAllComponents({ name: 'RouterLink' });
    // One for logo + 4 nav links = 5 total
    expect(links.length).toBe(5);
  });

  it('não quebra sem router (fallback)', () => {
    // Basic render test without router plugin (may show router-link stubs)
    const wrapper = mount(Navbar, {
      global: {
        stubs: ['router-link'],
      },
    });
    expect(wrapper.exists()).toBe(true);
  });
});
