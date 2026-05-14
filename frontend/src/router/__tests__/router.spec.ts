import { describe, it, expect, beforeEach } from 'vitest';
import { createRouter, createWebHistory } from 'vue-router';
import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/DashboardView.vue'),
  },
  {
    path: '/positions',
    name: 'Positions',
    component: () => import('@/views/PositionsView.vue'),
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('@/views/HistoryView.vue'),
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/SettingsView.vue'),
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFoundView.vue'),
  },
];

describe('Router', () => {
  let router: ReturnType<typeof createRouter>;

  beforeEach(async () => {
    router = createRouter({
      history: createWebHistory(),
      routes,
    });
  });

  it('rota / existe e tem nome Dashboard', () => {
    const route = router.resolve('/');
    expect(route.name).toBe('Dashboard');
  });

  it('rota /positions existe e tem nome Positions', () => {
    const route = router.resolve('/positions');
    expect(route.name).toBe('Positions');
  });

  it('rota /history existe e tem nome History', () => {
    const route = router.resolve('/history');
    expect(route.name).toBe('History');
  });

  it('rota /settings existe e tem nome Settings', () => {
    const route = router.resolve('/settings');
    expect(route.name).toBe('Settings');
  });

  it('rota /:pathMatch(.*)* captura rotas desconhecidas como NotFound', () => {
    const route = router.resolve('/pagina-inexistente');
    expect(route.name).toBe('NotFound');
  });

  it('rota /nonexistent/path também cai em NotFound', () => {
    const route = router.resolve('/algum/caminho/desconhecido');
    expect(route.name).toBe('NotFound');
  });

  it('navigation guard placeholder não bloqueia navegação', async () => {
    router.beforeEach((_to, _from, next) => {
      next();
    });

    await router.push('/positions');
    expect(router.currentRoute.value.name).toBe('Positions');
  });
});
