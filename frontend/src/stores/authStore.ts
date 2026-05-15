/**
 * AuthStore - Observer Pattern para gerenciamento de autenticação.
 *
 * Notifica componentes sobre mudanças de estado (login, logout, tokenExpired).
 * Componentes (Router, Navbar, API client) reagem ao mesmo estado sem conhecer-se.
 */

type EventCallback = (...args: unknown[]) => void;

export interface User {
  email: string;
  name?: string;
  role: string;
  authMethod: 'google' | 'fallback' | 'dev_bypass';
}

class AuthStore {
  private _token: string | null = null;
  private _user: User | null = null;
  private _listeners: Map<string, Set<EventCallback>> = new Map();

  constructor() {
    // Restaurar token do localStorage se existir
    this._token = localStorage.getItem('auth_token');
    if (this._token) {
      this._user = this._getUserFromToken(this._token);
    }
  }

  on(event: string, callback: EventCallback): () => void {
    if (!this._listeners.has(event)) {
      this._listeners.set(event, new Set());
    }
    this._listeners.get(event)!.add(callback);
    return () => this.off(event, callback);
  }

  off(event: string, callback: EventCallback): void {
    this._listeners.get(event)?.delete(callback);
  }

  emit(event: string, ...args: unknown[]): void {
    this._listeners.get(event)?.forEach((cb) => cb(...args));
  }

  get token(): string | null {
    return this._token;
  }

  get user(): User | null {
    return this._user;
  }

  get isAuthenticated(): boolean {
    return !!this._token;
  }

  /**
   * Inicia login OAuth - redireciona para Google
   */
  async loginWithGoogle(): Promise<void> {
    window.location.href = '/api/v1/auth/login';
  }

  /**
   * Trata callback do OAuth - troca código por JWT
   */
  async handleCallback(code: string, state?: string | null): Promise<void> {
    try {
      const response = await fetch('/api/v1/auth/callback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ code, state }),
      });

      if (!response.ok) {
        throw new Error('Falha na autenticação');
      }

      const data = await response.json();
      this.setToken(data.access_token);
      this.emit('loginSuccess', this._user!);
    } catch (error) {
      this.emit('loginFailed', error as Error);
      throw error;
    }
  }

  /**
   * Login via fallback (emergência)
   */
  async loginWithFallback(username: string, password: string): Promise<void> {
    try {
      const response = await fetch('/api/v1/auth/login-fallback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        throw new Error('Credenciais inválidas');
      }

      const data = await response.json();
      this.setToken(data.access_token);
      this.emit('loginSuccess', this._user!);
    } catch (error) {
      this.emit('loginFailed', error as Error);
      throw error;
    }
  }

  /**
   * Define o token e persiste
   */
  setToken(token: string): void {
    this._token = token;
    localStorage.setItem('auth_token', token);
    this._user = this._getUserFromToken(token);
  }

  /**
   * Remove o token e faz logout
   */
  logout(): void {
    this._token = null;
    this._user = null;
    localStorage.removeItem('auth_token');
    this.emit('logout');
  }

  /**
   * Inscreve para evento de token expirado
   */
  onTokenExpired(callback: () => void): () => void {
    this.on('tokenExpired', callback);
    return () => this.off('tokenExpired', callback);
  }

  /**
   * Decodifica JWT para obter informações do usuário
   */
  private _getUserFromToken(token: string): User | null {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return {
        email: payload.sub,
        name: payload.name,
        role: payload.role || 'user',
        authMethod: payload.auth_method || 'google',
      };
    } catch {
      return null;
    }
  }
}

// Singleton instance
export const authStore = new AuthStore();
