import { describe, it, expect } from 'vitest';

import router from '../index';

describe('auth router', () => {
  it('expõe a rota de callback OAuth da SPA', () => {
    const route = router.resolve('/api/auth/callback');

    expect(route.name).toBe('AuthCallback');
  });
});
