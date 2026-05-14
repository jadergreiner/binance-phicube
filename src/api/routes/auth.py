"""Auth routes - OAuth Google endpoints."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from src.api.auth.authenticator import get_authenticator
from src.api.auth.jwt_handler import create_token, verify_token
from src.api.auth.recovery.emergency_facade import get_emergency_facade
from src.config.settings import get_settings


router = APIRouter(prefix="/auth", tags=["auth"])


class LoginFallbackRequest(BaseModel):
    """Requisição de login fallback."""

    username: str
    password: str


class CallbackRequest(BaseModel):
    """Requisição de callback OAuth."""

    code: str


@router.get("/login")
async def login(request: Request):
    """Inicia fluxo OAuth - redireciona para Google."""
    settings = get_settings()

    # Se dev bypass ativo, redirecionar para callback direto
    if settings.auth_dev_bypass:
        return RedirectResponse(url="/auth/callback?code=dev")

    authenticator = get_authenticator()
    result = await authenticator.authenticate(request)

    if result.error == "redirect":
        # Retorna URL de autorização para o frontend redirecionar
        return {"authorization_url": result.user}

    if not result.success:
        raise HTTPException(status_code=401, detail=result.error)

    return {"access_token": result.token, "token_type": "bearer"}


@router.get("/callback")
async def callback(request: Request):
    """Callback do OAuth - processa código e retorna JWT."""
    settings = get_settings()

    # Dev bypass mode
    if settings.auth_dev_bypass:
        authenticator = get_authenticator()
        result = await authenticator.authenticate(request)

        if result.success:
            return {"access_token": result.token, "token_type": "bearer"}
        raise HTTPException(status_code=401, detail=result.error)

    # OAuth mode
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Código não fornecido")

    authenticator = get_authenticator()
    result = await authenticator.authenticate(request)

    if not result.success:
        raise HTTPException(status_code=401, detail=result.error)

    return {"access_token": result.token, "token_type": "bearer"}


@router.post("/callback")
async def callback_post(request: CallbackRequest):
    """Callback do OAuth via POST (para frontend)."""
    settings = get_settings()

    # Dev bypass mode
    if settings.auth_dev_bypass:
        authenticator = get_authenticator()
        result = await authenticator.authenticate(Request)  # Simplified

        if result.success:
            return {"access_token": result.token, "token_type": "bearer"}
        raise HTTPException(status_code=401, detail=result.error)

    # OAuth mode - criar request fake com code
    from fastapi import Query

    class FakeRequest:
        def __init__(self, code: str):
            self.query_params = {"code": code}

    authenticator = get_authenticator()
    result = await authenticator.authenticate(FakeRequest(code=request.code))

    if not result.success:
        raise HTTPException(status_code=401, detail=result.error)

    return {"access_token": result.token, "token_type": "bearer"}


@router.post("/refresh")
async def refresh(request: Request):
    """Renova JWT token."""
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token não fornecido")

    token = auth_header.replace("Bearer ", "")

    try:
        payload = verify_token(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    # Gerar novo token
    new_token = create_token(
        subject=payload.sub,
        auth_method=payload.auth_method,
        role=payload.role,
    )

    return {"access_token": new_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(request: Request):
    """Revoga sessão (cliente remove token)."""
    # JWT é stateless - logout é simplesmente remover token do cliente
    # Em produção, poderia adicionar token a uma blacklist
    return {"message": "Logout realizado"}


@router.get("/me")
async def me(request: Request):
    """Retorna informações do usuário logado."""
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token não fornecido")

    token = auth_header.replace("Bearer ", "")

    try:
        payload = verify_token(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    return {
        "email": payload.sub,
        "role": payload.role,
        "auth_method": payload.auth_method,
    }


@router.post("/login-fallback")
async def login_fallback(req: LoginFallbackRequest):
    """Login de emergência quando conta Google está inacessível."""
    facade = get_emergency_facade()
    result = await facade.login_with_fallback(req.username, req.password)

    if not result.success:
        raise HTTPException(status_code=401, detail=result.error)

    return {"access_token": result.token, "token_type": "bearer"}