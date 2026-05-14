import { describe, it, expect, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useUiStore } from '../uiStore';

describe('uiStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('inicia com tema light', () => {
    const store = useUiStore();
    expect(store.theme).toBe('light');
  });

  it('toggleTheme alterna para dark', () => {
    const store = useUiStore();
    store.toggleTheme();
    expect(store.theme).toBe('dark');
  });

  it('toggleTheme alterna de volta para light', () => {
    const store = useUiStore();
    store.toggleTheme();
    store.toggleTheme();
    expect(store.theme).toBe('light');
  });

  it('sidebar começa aberta', () => {
    const store = useUiStore();
    expect(store.sidebarOpen).toBe(true);
  });

  it('toggleSidebar alterna estado', () => {
    const store = useUiStore();
    store.toggleSidebar();
    expect(store.sidebarOpen).toBe(false);
    store.toggleSidebar();
    expect(store.sidebarOpen).toBe(true);
  });

  it('addNotification adiciona notificação', () => {
    const store = useUiStore();
    store.addNotification('Teste mensagem', 'info');
    expect(store.notifications.length).toBe(1);
    expect(store.notifications[0].message).toBe('Teste mensagem');
    expect(store.notifications[0].type).toBe('info');
  });

  it('addNotification usa tipo padrão info', () => {
    const store = useUiStore();
    store.addNotification('Mensagem');
    expect(store.notifications[0].type).toBe('info');
  });

  it('addNotification adiciona tipo warning', () => {
    const store = useUiStore();
    store.addNotification('Aviso', 'warning');
    expect(store.notifications[0].type).toBe('warning');
  });

  it('addNotification adiciona tipo error', () => {
    const store = useUiStore();
    store.addNotification('Erro', 'error');
    expect(store.notifications[0].type).toBe('error');
  });

  it('removeNotification remove por id', () => {
    const store = useUiStore();
    store.addNotification('Notif 1', 'info');
    store.addNotification('Notif 2', 'warning');
    const idToRemove = store.notifications[0].id;
    store.removeNotification(idToRemove);
    expect(store.notifications.length).toBe(1);
    expect(store.notifications[0].message).toBe('Notif 2');
  });

  it('addNotification gera id único', () => {
    const store = useUiStore();
    store.addNotification('A', 'info');
    store.addNotification('B', 'info');
    expect(store.notifications[0].id).not.toBe(store.notifications[1].id);
  });
});
