/**
 * uiStore — Gerenciamento de estado da interface
 *
 * Store Pinia para controle de tema, sidebar e notificações.
 */
import { defineStore } from 'pinia';
import { ref } from 'vue';

export interface Notification {
  id: string;
  message: string;
  type: 'info' | 'warning' | 'error';
  timestamp: Date;
}

export const useUiStore = defineStore('ui', () => {
  // State
  const theme = ref<'light' | 'dark'>('light');
  const sidebarOpen = ref(true);
  const notifications = ref<Notification[]>([]);

  // Actions
  function toggleTheme() {
    theme.value = theme.value === 'light' ? 'dark' : 'light';
  }

  function toggleSidebar() {
    sidebarOpen.value = !sidebarOpen.value;
  }

  function addNotification(msg: string, type: 'info' | 'warning' | 'error' = 'info') {
    const id = `notif-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    notifications.value.push({
      id,
      message: msg,
      type,
      timestamp: new Date(),
    });
  }

  function removeNotification(id: string) {
    notifications.value = notifications.value.filter((n) => n.id !== id);
  }

  return {
    theme,
    sidebarOpen,
    notifications,
    toggleTheme,
    toggleSidebar,
    addNotification,
    removeNotification,
  };
});
