import { beforeEach, describe, expect, it, vi } from 'vitest';

import { authStore } from '../authStore';

describe('authStore', () => {
  beforeEach(() => {
    localStorage.clear();
    authStore.logout();
    vi.restoreAllMocks();
  });

  it('completeLogin armazena o token retornado pelo backend', () => {
    const tokenPayload = {
      sub: 'user@example.com',
      role: 'admin',
      auth_method: 'google',
    };
    const token = ['header', btoa(JSON.stringify(tokenPayload)), 'signature'].join('.');

    authStore.completeLogin(token);

    expect(authStore.token).toBe(token);
    expect(authStore.user?.email).toBe('user@example.com');
    expect(authStore.user?.authMethod).toBe('google');
  });
});
