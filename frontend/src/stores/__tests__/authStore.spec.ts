import { beforeEach, describe, expect, it, vi } from 'vitest';

import { authStore } from '../authStore';

describe('authStore', () => {
  beforeEach(() => {
    localStorage.clear();
    authStore.logout();
    vi.restoreAllMocks();
  });

  it('handleCallback envia code e state para a API e armazena o token', async () => {
    const tokenPayload = {
      sub: 'user@example.com',
      role: 'admin',
      auth_method: 'google',
    };
    const token = ['header', btoa(JSON.stringify(tokenPayload)), 'signature'].join('.');

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({
        access_token: token,
      }),
    });

    vi.stubGlobal('fetch', fetchMock);

    await authStore.handleCallback('code-123', 'state-123');

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/auth/callback', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        code: 'code-123',
        state: 'state-123',
      }),
    });
    expect(authStore.token).toBe(token);
    expect(authStore.user?.email).toBe('user@example.com');
    expect(authStore.user?.authMethod).toBe('google');
  });
});
