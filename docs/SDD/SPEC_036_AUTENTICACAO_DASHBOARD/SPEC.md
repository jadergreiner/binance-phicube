# SPEC_036 — Autenticação OAuth Google no Dashboard

**ID:** SPEC_036
**Título:** Autenticação OAuth Google no Dashboard
**Data:** 2026-05-14
**Status:** Rascunho
**Versão:** 2.0
**Dependências:** SPEC_014 (security design), SPEC_020 (hardening governança)
**PRD §:** Fase 2 — "Segurança de acesso"

---

## 1. Objetivo

Adicionar autenticação baseada em OAuth Google ao dashboard e à API REST, garantindo que apenas usuários com conta Google autorizada acessem informações de posições, trades e configuração do bot.

**Decisão de arquitetura:** OAuth Google em vez de login simples, com modo dev bypass para desenvolvimento local.

---

## 2. Escopo

### Dentro do escopo
- Login via OAuth Google (`GET /auth/login` → redirect → callback → JWT)
- Middleware de verificação JWT nas rotas protegidas (`/api/v1/*`)
- Rota `/auth/refresh` para renovar token
- Rota `/auth/logout` para revogar sessão
- Rota `/auth/me` para retornar usuário logado
- Modo dev bypass (`AUTH_DEV_BYPASS=true`) para desenvolvimento local
- Lista de emails autorizados (`AUTH_ALLOWED_EMAILS`)
- Usuário fallback para recovery (`AUTH_FALLBACK_USER`, `AUTH_FALLBACK_PASSWORD`)
- Config: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `JWT_SECRET`, `AUTH_ALLOWED_EMAILS`, `AUTH_DEV_BYPASS`, `AUTH_FALLBACK_*`
- Exceção: `/health`, `/metrics`, `/docs` permanecem públicas
- Frontend: botão "Login com Google" + AuthStore (Observer Pattern)

### Fora do escopo
- OAuth com outros provedores (GitHub, etc) — preparado mas não implementado
- 2FA (autenticação de dois fatores)
- Roles/permissões por usuário (admin vs viewer)
- Rate limiting no login (será tratado em SPEC de segurança)

---

## 3. User Stories

### US-036-01 — Login OAuth Google
**Como** operador,
**quero** fazer login com minha conta Google,
**para** acessar o dashboard de forma segura.

**Critério de aceite:**
- `GET /auth/login` → redirect para Google OAuth
- Callback com código válido → 200 + JWT
- Callback com código inválido → 401
- JWT expira em 24h (configurável)

### US-036-02 — Lista de autorizados
**Como** operador,
**quero** definir quais emails podem acessar o dashboard,
**para** controlar quem tem acesso.

**Critério de aceite:**
- `AUTH_ALLOWED_EMAILS` configurado → apenas emails na lista têm acesso
- Email não autorizado → 403 Forbidden

### US-036-03 — Modo desenvolvimento
**Como** desenvolvedor,
**quero** fazer login sem OAuth Google em desenvolvimento,
**para** testar o dashboard rapidamente.

**Critério de aceite:**
- `AUTH_DEV_BYPASS=true` → login simples funciona
- Health check alerta se bypass ativo em produção

### US-036-04 — Recovery
**Como** operador,
**quero** acessar o dashboard se minha conta Google ficar inacessível,
**para** não ficar trancado fora do sistema.

**Critério de aceite:**
- `POST /auth/login-fallback` com credenciais de emergência → JWT
- Toda tentativa de fallback é logada para auditoria

### US-036-05 — Rotas protegidas
**Como** operador,
**quero** que a API rejeite requisições sem token,
**para** que dados sensíveis não fiquem expostos.

**Critério de aceite:**
- `GET /api/v1/positions` sem token → 401
- `GET /api/v1/positions` com token válido → 200
- `GET /api/v1/positions` com token expirado → 401
- `/health` sempre → 200 (público)

---

## 4. Modelo de Dados

### Config (`src/config/settings.py`)

```python
# OAuth Google
GOOGLE_CLIENT_ID: str = Field(default=..., alias="GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET: str = Field(default=..., alias="GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI: str = Field(default=..., alias="GOOGLE_REDIRECT_URI")

# Segurança
AUTH_ALLOWED_EMAILS: list[str] = Field(default=[], alias="AUTH_ALLOWED_EMAILS")
AUTH_DEV_BYPASS: bool = Field(default=False, alias="AUTH_DEV_BYPASS")

# Fallback para recovery
AUTH_FALLBACK_USER: str = Field(default="", alias="AUTH_FALLBACK_USER")
AUTH_FALLBACK_PASSWORD_HASH: str = Field(default="", alias="AUTH_FALLBACK_PASSWORD_HASH")

# JWT
JWT_SECRET: str = Field(default=..., alias="JWT_SECRET")
JWT_ALGORITHM: str = "HS256"
JWT_EXPIRY_HOURS: int = 24
```

### Payload do JWT

```python
@dataclass
class TokenPayload:
    sub: str          # Email do usuário
    exp: datetime     # Data de expiração
    iat: datetime     # Data de emissão
    role: str = "user"
    auth_method: str = "google" | "fallback"
```

---

## 5. Design Patterns Adotados

| Pattern  | Aplicação                            | Benefício                 |
| -------- | ------------------------------------ | ------------------------- |
| Adapter  | OAuthProvider abstraction           | Troca de provider futura  |
| Strategy | Auth strategies (OAuth/Dev/Fallback) | Runtime switching, testes |
| Facade   | Emergency login                      | Simplicidade, auditoria   |
| Observer | Auth state (frontend)                | Componentes desacoplados  |
| Factory  | Test data builders                   | Testes reutilizáveis      |

---

## 6. Componentes

### 6.1 OAuth Provider (Adapter Pattern)

```python
# src/api/auth/oauth_provider.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class OAuthToken:
    access_token: str
    id_token: str
    expires_in: int
    token_type: str

@dataclass
class UserInfo:
    email: str
    name: str | None
    picture: str | None

class OAuthProvider(ABC):
    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        pass

    @abstractmethod
    def exchange_code(self, code: str) -> OAuthToken:
        pass

    @abstractmethod
    def get_user_info(self, token: OAuthToken) -> UserInfo:
        pass
```

```python
# src/api/auth/providers/google_oauth.py
class GoogleOAuthProvider(OAuthProvider):
    def get_authorization_url(self, state: str) -> str:
        # Construir URL de autorização Google
        pass

    def exchange_code(self, code: str) -> OAuthToken:
        # Trocar código por token
        pass

    def get_user_info(self, token: OAuthToken) -> UserInfo:
        # Buscar info do usuário
        pass
```

### 6.2 Auth Strategies (Strategy Pattern)

```python
# src/api/auth/strategies/auth_strategy.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class AuthResult:
    success: bool
    token: str | None = None
    user: str | None = None
    error: str | None = None

class AuthStrategy(ABC):
    @abstractmethod
    async def authenticate(self, request: Request) -> AuthResult:
        pass
```

```python
# src/api/auth/strategies/oauth_strategy.py
class OAuthStrategy(AuthStrategy):
    async def authenticate(self, request: Request) -> AuthResult:
        # Implementar autenticação OAuth
        pass
```

```python
# src/api/auth/strategies/dev_bypass_strategy.py
class DevBypassStrategy(AuthStrategy):
    async def authenticate(self, request: Request) -> AuthResult:
        # Implementar bypass para desenvolvimento
        pass
```

```python
# src/api/auth/authenticator.py
class Authenticator:
    def __init__(self, strategy: AuthStrategy):
        self._strategy = strategy

    def set_strategy(self, strategy: AuthStrategy):
        self._strategy = strategy

    async def authenticate(self, request: Request) -> AuthResult:
        return await self._strategy.authenticate(request)
```

### 6.3 Validators (Chain of Responsibility)

```python
# src/api/auth/validators/auth_validator.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class ValidationResult:
    valid: bool
    error: str | None = None

class AuthValidator(ABC):
    _next: AuthValidator | None = None

    def set_next(self, validator: AuthValidator) -> AuthValidator:
        self._next = validator
        return validator

    async def validate(self, email: str) -> ValidationResult:
        result = await self._validate(email)
        if not result.valid and self._next:
            return await self._next.validate(email)
        return result

    @abstractmethod
    async def _validate(self, email: str) -> ValidationResult:
        pass
```

```python
# src/api/auth/validators/allowed_list_validator.py
class AllowedListValidator(AuthValidator):
    async def _validate(self, email: str) -> ValidationResult:
        if email in settings.AUTH_ALLOWED_EMAILS:
            return ValidationResult(valid=True)
        return ValidationResult(valid=False, error="Email não autorizado")
```

### 6.4 Recovery Facade (Facade Pattern)

```python
# src/api/auth/recovery/emergency_facade.py
class EmergencyFacade:
    async def login_with_fallback(self, username: str, password: str) -> AuthResult:
        # Validar credenciais de fallback
        # Gerar JWT
        # Logar para auditoria
        pass

    async def report_lost_access(self, user: str):
        # Notificar admin
        # Log de incidente
        pass
```

### 6.5 Endpoints

```python
# src/api/routes/auth.py
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/login")
async def login(request: Request):
    # Redirect para Google OAuth
    pass

@router.get("/callback")
async def callback(code: str, state: str):
    # Trocar code por token, gerar JWT, redirecionar
    pass

@router.post("/refresh")
async def refresh(token: TokenPayload = Depends(verify_token)):
    # Renovar JWT
    pass

@router.post("/logout")
async def logout(token: TokenPayload = Depends(verify_token)):
    # Revogar sessão
    pass

@router.get("/me")
async def me(token: TokenPayload = Depends(verify_token)):
    # Retornar usuário logado
    pass

@router.post("/login-fallback")
async def login_fallback(req: LoginFallbackRequest):
    # Login de emergência
    pass
```

### 6.6 Frontend (Observer Pattern)

```typescript
// frontend/src/stores/auth-store.ts
import { EventEmitter } from 'events';

interface AuthEvents {
  loginSuccess: User;
  loginFailed: Error;
  logout: void;
  tokenExpired: void;
}

class AuthStore extends EventEmitter<AuthEvents> {
  private _token: string | null = null;
  private _user: User | null = null;

  get token() { return this._token; }
  get user() { return this._user; }
  get isAuthenticated() { return !!this._token; }

  async loginWithGoogle(): Promise<void> {
    window.location.href = '/auth/login';
  }

  async handleCallback(code: string): Promise<void> {
    // Trocar code por JWT
    // Emitir evento loginSuccess
  }

  logout(): void {
    this._token = null;
    this._user = null;
    this.emit('logout');
  }

  onTokenExpired(callback: () => void): void {
    this.on('tokenExpired', callback);
  }
}

export const authStore = new AuthStore();
```

```typescript
// frontend/src/components/AuthObserver.vue
export default {
  mounted() {
    authStore.on('tokenExpired', () => {
      router.push('/login');
    });
  }
};
```

---

## 7. Invariantes

| ID | Invariante |
|----|-----------|
| INV-036-01 | Senha nunca é armazenada em plain text — sempre bcrypt |
| INV-036-02 | JWT secret nunca aparece em logs |
| INV-036-03 | `/health` e `/metrics` sempre públicos |
| INV-036-04 | `AUTH_DEV_BYPASS=true` → health check alerta |
| INV-036-05 | Toda tentativa de fallback é logada para auditoria |
| INV-036-06 | Google OAuth client secret validado em startup |

---

## 8. Testes

| ID | Descrição |
|----|-----------|
| TEST_036_01 | Login OAuth com código válido → 200 + JWT |
| TEST_036_02 | Login OAuth com código inválido → 401 |
| TEST_036_03 | Email não autorizado → 403 |
| TEST_036_04 | Rota protegida sem token → 401 |
| TEST_036_05 | Rota protegida com token válido → 200 |
| TEST_036_06 | Rota protegida com token expirado → 401 |
| TEST_036_07 | `/health` acessível sem token |
| TEST_036_08 | `AUTH_DEV_BYPASS=true` → login simples funciona |
| TEST_036_09 | `AUTH_DEV_BYPASS=true` em produção → health check alerta |
| TEST_036_10 | Fallback login → log de auditoria |

---

## 9. Arquivos

| Arquivo | Mudança |
|---------|---------|
| `src/api/auth/oauth_provider.py` | Criado — interface abstrata OAuthProvider |
| `src/api/auth/providers/google_oauth.py` | Criado — implementação Google |
| `src/api/auth/strategies/auth_strategy.py` | Criado — interface AuthStrategy |
| `src/api/auth/strategies/oauth_strategy.py` | Criado — OAuthStrategy |
| `src/api/auth/strategies/dev_bypass_strategy.py` | Criado — DevBypassStrategy |
| `src/api/auth/authenticator.py` | Criado — seleciona strategy |
| `src/api/auth/validators/auth_validator.py` | Criado — interface Validator |
| `src/api/auth/validators/allowed_list_validator.py` | Criado — validação de lista |
| `src/api/auth/recovery/emergency_facade.py` | Criado — recovery facade |
| `src/api/routes/auth.py` | Modificado — endpoints OAuth |
| `src/api/dependencies.py` | Modificado — get_current_user |
| `src/api/main.py` | Modificado — incluir auth router + strategies |
| `src/config/settings.py` | Modificado — OAuth configs |
| `frontend/src/stores/auth-store.ts` | Criado — AuthStore (Observer) |
| `frontend/src/views/LoginView.vue` | Modificado — botão Google |
| `frontend/src/services/api.ts` | Modificado — Authorization header |
| `frontend/src/router/index.ts` | Modificado — auth guard |
| `frontend/src/components/AuthObserver.vue` | Criado — escuta tokenExpired |
| `tests/factories/oauth_response_factory.py` | Criado — factory para testes |
| `tests/builders/user_info_builder.py` | Criado — builder para testes |
| `tests/api/test_oauth.py` | Criado — TEST_036_01 a 10 |
| `pyproject.toml` | Modificado — adicionar `authlib`, `httpx` |

---

## 10. Definition of Done

- [ ] `GET /auth/login` redirect para Google OAuth
- [ ] Callback processa código e retorna JWT
- [ ] Lista de autorizados valida email
- [ ] Modo dev bypass funciona com alerta
- [ ] Fallback para recovery com auditoria
- [ ] Frontend com AuthStore (Observer)
- [ ] Health check alerta se bypass ativo
- [ ] TEST_036_01 a 10 passando
- [ ] `ruff check src/ tests/` limpo
- [ ] JWT secret não aparece em logs

---

## 11. Configuração OAuth Google

### Google Cloud Console

1. Criar projeto ou selecionar existente
2. APIs e Serviços → Credenciais
3. Criar Credenciais → ID do cliente OAuth
4. Tipo de aplicação: Aplicação web
5. URIs de redirecionamento autorizados:
   - `http://localhost:8080/auth/callback` (desenvolvimento)
   - `https://seudominio.com/auth/callback` (produção)
6. Escopos: `openid`, `email`, `profile`

### Variáveis .env

```bash
# OAuth Google (obrigatório em produção)
GOOGLE_CLIENT_ID=seu-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=seu-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8080/auth/callback

# Segurança
AUTH_ALLOWED_EMAILS=seuemail@gmail.com,outro@email.com
AUTH_DEV_BYPASS=false

# Fallback (apenas para recovery)
AUTH_FALLBACK_USER=emergency
AUTH_FALLBACK_PASSWORD_HASH=$2b$12$...

# JWT
JWT_SECRET=gerar-string-segura-aqui
```