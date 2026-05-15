"""Auth routes - OAuth Google endpoints."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

from src.api.auth.authenticator import get_authenticator
from src.api.auth.jwt_handler import create_token, verify_token
from src.api.auth.recovery.emergency_facade import get_emergency_facade
from src.config.settings import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])

_OAUTH_STATE_COOKIE = "phicube_oauth_state"
_OAUTH_STATE_COOKIE_PATH = "/"
_OAUTH_STATE_COOKIE_MAX_AGE_SECONDS = 300


class LoginFallbackRequest(BaseModel):
    """Requisição de login fallback."""

    username: str
    password: str


class CallbackRequest(BaseModel):
    """Requisição de callback OAuth."""

    code: str
    state: str | None = None


@dataclass(slots=True)
class _QueryRequest:
    query_params: dict[str, str]


def _frontend_callback_url() -> str:
    settings = get_settings()
    return settings.google_redirect_uri or "/api/auth/callback"


def _cookie_matches_state(request: Request, state: str | None) -> bool:
    cookie_state = request.cookies.get(_OAUTH_STATE_COOKIE)
    return bool(state and cookie_state and state == cookie_state)


def _clear_state_cookie(response: JSONResponse) -> None:
    response.delete_cookie(_OAUTH_STATE_COOKIE, path=_OAUTH_STATE_COOKIE_PATH)


async def _complete_callback(request: Request, code: str, state: str | None) -> JSONResponse:
    settings = get_settings()

    if not settings.auth_dev_bypass and not _cookie_matches_state(request, state):
        raise HTTPException(status_code=401, detail="State inválido")

    authenticator = get_authenticator()
    result = await authenticator.authenticate(
        _QueryRequest(query_params={"code": code, "state": state or ""})
    )

    if not result.success:
        raise HTTPException(status_code=401, detail=result.error)

    response = JSONResponse({"access_token": result.token, "token_type": "bearer"})
    _clear_state_cookie(response)
    return response


@router.get("/login")
async def login(request: Request):
    """Inicia fluxo OAuth - redireciona para Google ou para o callback local no modo dev."""
    settings = get_settings()

    if settings.auth_dev_bypass:
        callback_url = _frontend_callback_url()
        return RedirectResponse(url=f"{callback_url}?code=dev&state=dev")

    authenticator = get_authenticator()
    result = await authenticator.authenticate(request)

    if result.error == "redirect":
        if not result.user:
            raise HTTPException(status_code=500, detail="URL de autorização ausente")
        if not result.state:
            raise HTTPException(status_code=500, detail="State OAuth ausente")

        response = RedirectResponse(url=result.user)
        response.set_cookie(
            key=_OAUTH_STATE_COOKIE,
            value=result.state,
            max_age=_OAUTH_STATE_COOKIE_MAX_AGE_SECONDS,
            httponly=True,
            samesite="lax",
            path=_OAUTH_STATE_COOKIE_PATH,
        )
        return response

    if not result.success:
        raise HTTPException(status_code=401, detail=result.error)

    return {"access_token": result.token, "token_type": "bearer"}


@router.get("/callback")
async def callback_get(request: Request):
    """Callback do OAuth via GET."""
    code = request.query_params.get("code")
    state = request.query_params.get("state")

    if not code:
        raise HTTPException(status_code=400, detail="Código não fornecido")

    return await _complete_callback(request, code, state)


@router.post("/callback")
async def callback_post(request: Request, payload: CallbackRequest):
    """Callback do OAuth via POST (para frontend)."""
    return await _complete_callback(request, payload.code, payload.state)


@router.post("/refresh")
async def refresh(request: Request):
    """Renova JWT token."""
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token não fornecido")

    token = auth_header.replace("Bearer ", "")

    try:
        payload = verify_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    new_token = create_token(
        subject=payload.sub,
        auth_method=payload.auth_method,
        role=payload.role,
    )

    return {"access_token": new_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(request: Request):
    """Revoga sessão (cliente remove token)."""
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
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

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
