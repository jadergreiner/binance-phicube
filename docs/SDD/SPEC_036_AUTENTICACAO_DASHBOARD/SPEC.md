# SPEC_036 — Autenticação no Dashboard

**ID:** SPEC_036
**Título:** Autenticação no Dashboard
**Data:** 2026-05-10
**Status:** Rascunho
**Versão:** 1.0
**Dependências:** SPEC_014 (security design), SPEC_020 (hardening governança)
**PRD §:** Fase 2 — "Segurança de acesso"

---

## 1. Objetivo

Adicionar autenticação baseada em JWT (JSON Web Token) ao dashboard e à API REST, garantindo que apenas usuários autorizados acessem informações de posições, trades e configuração do bot.

Atualmente todos os endpoints da dashboard API (`/api/v1/*`) são públicos — qualquer pessoa com acesso à rede pode ver posições e saldo.

---

## 2. Escopo

### Dentro do escopo
- Login com usuário/senha via `POST /auth/login` → JWT
- Middleware de verificação JWT nas rotas protegidas (`/api/v1/*`)
- Rota `/auth/refresh` para renovar token
- Config: `AUTH_ENABLED` (bool), `AUTH_USERNAME`, `AUTH_PASSWORD_HASH`, `JWT_SECRET`
- Exceção: `/health`, `/metrics`, `/docs` permanecem públicas
- Frontend: tela de login + armazenamento do token em memória/httpOnly cookie

### Fora do escopo
- OAuth2 / SSO (Google, GitHub)
- 2FA (autenticação de dois fatores)
- Roles/permissões por usuário (admin vs viewer)
- Rate limiting no login (será tratado em SPEC de segurança)

---

## 3. User Stories

### US-036-01 — Login protegido
**Como** operador,
**quero** fazer login com usuário e senha,
**para** acessar o dashboard de forma segura.

**Critério de aceite:**
- `POST /auth/login` com credenciais válidas → 200 + JWT
- `POST /auth/login` com credenciais inválidas → 401
- JWT expira em 24h (configurável)

### US-036-02 — Rotas protegidas
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
AUTH_ENABLED: bool = True
AUTH_USERNAME: str = "admin"
AUTH_PASSWORD_HASH: str = ""   # bcrypt hash, gerado via CLI ou env
JWT_SECRET: str = Field(default=..., alias="JWT_SECRET")  # Obrigatório
JWT_ALGORITHM: str = "HS256"
JWT_EXPIRY_HOURS: int = 24
```

### Payload do JWT

```python
@dataclass
class TokenPayload:
    sub: str          # Username
    exp: datetime     # Data de expiração
    iat: datetime     # Data de emissão
    role: str = "admin"
```

---

## 5. Componentes

### 5.1 `src/api/auth.py` — novo módulo

```python
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def create_token(username: str, secret: str, expiry_hours: int = 24) -> str:
    payload = {
        "sub": username,
        "exp": datetime.utcnow() + timedelta(hours=expiry_hours),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, secret, algorithm="HS256")

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> TokenPayload:
    try:
        payload = jwt.decode(credentials.credentials, settings.JWT_SECRET, algorithms=["HS256"])
        return TokenPayload(**payload)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")
```

### 5.2 `src/api/routes/auth.py` — endpoints

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
async def login(req: LoginRequest, settings = Depends(get_settings)):
    if not settings.AUTH_ENABLED:
        return {"access_token": "", "token_type": "disabled"}
    if req.username != settings.AUTH_USERNAME:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    if not pwd_context.verify(req.password, settings.AUTH_PASSWORD_HASH):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    token = create_token(req.username, settings.JWT_SECRET)
    return {"access_token": token, "token_type": "bearer"}

@router.post("/refresh")
async def refresh(token: TokenPayload = Depends(verify_token)):
    new_token = create_token(token.sub, settings.JWT_SECRET)
    return {"access_token": new_token, "token_type": "bearer"}
```

### 5.3 Middleware nas rotas protegidas

```python
# src/api/dependencies.py
from src.api.auth import verify_token

def get_current_user(token: TokenPayload = Depends(verify_token)) -> TokenPayload:
    if not settings.AUTH_ENABLED:
        return TokenPayload(sub="anonymous", exp=datetime.max, iat=datetime.min)
    return token

# src/api/main.py — aplicar nas rotas /api/v1
app.include_router(auth_router)
app.include_router(positions_router, dependencies=[Depends(get_current_user)])
app.include_router(trades_router, dependencies=[Depends(get_current_user)])
```

### 5.4 Frontend — tela de login

```typescript
// frontend/src/views/LoginView.vue
// - Formulário username + password
// - POST /auth/login
// - Token armazenado em memória (variável reativa)
// - Redireciona para /dashboard após login
```

---

## 6. Invariantes

| ID | Invariante |
|----|-----------|
| INV-036-01 | Senha nunca é armazenada em plain text — sempre bcrypt |
| INV-036-02 | JWT secret nunca aparece em logs |
| INV-036-03 | `/health` e `/metrics` sempre públicos |
| INV-036-04 | `AUTH_ENABLED=False` → qualquer requisição passa (dev mode) |

---

## 7. Testes

| ID | Descrição |
|----|-----------|
| TEST_036_01 | Login com credenciais válidas → 200 + token |
| TEST_036_02 | Login com senha errada → 401 |
| TEST_036_03 | Rota protegida sem token → 401 |
| TEST_036_04 | Rota protegida com token válido → 200 |
| TEST_036_05 | Rota protegida com token expirado → 401 |
| TEST_036_06 | `/health` acessível sem token |
| TEST_036_07 | `AUTH_ENABLED=False` → rotas protegidas acessíveis sem token |

---

## 8. Arquivos

| Arquivo | Mudança |
|---------|---------|
| `src/api/auth.py` | Criado — create_token, verify_token |
| `src/api/routes/auth.py` | Criado — POST /auth/login, POST /auth/refresh |
| `src/api/dependencies.py` | Modificado — get_current_user |
| `src/api/main.py` | Modificado — incluir auth router + dependencies |
| `src/config/settings.py` | Modificado — `AUTH_*`, `JWT_SECRET` |
| `frontend/src/views/LoginView.vue` | Criado — tela de login |
| `frontend/src/services/api.ts` | Modificado — incluir token no header |
| `frontend/src/router/index.ts` | Modificado — guard de autenticação |
| `tests/api/test_auth.py` | Criado — TEST_036_01 a 07 |
| `pyproject.toml` | Modificado — adicionar `pyjwt`, `passlib`, `bcrypt` |

---

## 9. Definition of Done

- [ ] `POST /auth/login` funcional com bcrypt + JWT
- [ ] Middleware protege `/api/v1/*` exceto health/metrics
- [ ] Frontend com tela de login e guard de rota
- [ ] `AUTH_ENABLED=False` modo dev sem auth
- [ ] TEST_036_01 a 07 passando
- [ ] `ruff check src/ tests/` limpo
- [ ] JWT secret não aparece em logs
