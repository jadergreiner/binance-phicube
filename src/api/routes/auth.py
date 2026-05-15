"""Auth routes - OAuth Google endpoints."""

from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel

from src.api.auth.authenticator import get_authenticator
from src.api.auth.jwt_handler import create_token, verify_token
from src.api.auth.recovery.emergency_facade import get_emergency_facade
from src.config.settings import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])

_OAUTH_STATE_COOKIE = "phicube_oauth_state"
_POST_LOGIN_REDIRECT_COOKIE = "phicube_post_login_redirect"
_OAUTH_STATE_COOKIE_PATH = "/"
_OAUTH_STATE_COOKIE_MAX_AGE_SECONDS = 300


class LoginFallbackRequest(BaseModel):
    """Requisição de login fallback."""

    username: str
    password: str


def _post_login_redirect_target(request: Request) -> str:
    redirect_target = request.query_params.get("redirect")
    if redirect_target and redirect_target.startswith("/"):
        return redirect_target
    return "/"


def _cookie_matches_state(request: Request, state: str | None) -> bool:
    cookie_state = request.cookies.get(_OAUTH_STATE_COOKIE)
    return bool(state and cookie_state and state == cookie_state)


def _clear_state_cookie(response: Response) -> None:
    response.delete_cookie(_OAUTH_STATE_COOKIE, path=_OAUTH_STATE_COOKIE_PATH)
    response.delete_cookie(_POST_LOGIN_REDIRECT_COOKIE, path=_OAUTH_STATE_COOKIE_PATH)


def _build_frontend_redirect_url(access_token: str, redirect_target: str) -> str:
    settings = get_settings()
    query = urlencode({"access_token": access_token, "redirect": redirect_target})
    return f"{settings.auth_post_login_redirect_uri}?{query}"


@router.get("/login")
async def login(request: Request):
    """Inicia fluxo OAuth - redireciona para Google ou para o callback local no modo dev."""
    settings = get_settings()

    if settings.auth_dev_bypass:
        jwt_token = create_token(subject="dev@localhost", auth_method="dev_bypass")
        redirect_target = request.cookies.get(_POST_LOGIN_REDIRECT_COOKIE) or "/"
        return RedirectResponse(
            url=_build_frontend_redirect_url(jwt_token, redirect_target),
            status_code=302,
        )

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
        response.set_cookie(
            key=_POST_LOGIN_REDIRECT_COOKIE,
            value=_post_login_redirect_target(request),
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

    settings = get_settings()
    if settings.auth_dev_bypass:
        jwt_token = create_token(subject="dev@localhost", auth_method="dev_bypass")
        redirect_target = request.cookies.get(_POST_LOGIN_REDIRECT_COOKIE) or "/"
        response = RedirectResponse(
            url=_build_frontend_redirect_url(jwt_token, redirect_target), status_code=302
        )
        _clear_state_cookie(response)
        return response

    if not _cookie_matches_state(request, state):
        raise HTTPException(status_code=401, detail="State inválido")

    authenticator = get_authenticator()
    result = await authenticator.authenticate(request)

    if not result.success:
        raise HTTPException(status_code=401, detail=result.error)

    if not result.token:
        raise HTTPException(status_code=500, detail="Token JWT ausente")

    redirect_target = request.cookies.get(_POST_LOGIN_REDIRECT_COOKIE) or "/"
    response = RedirectResponse(
        url=_build_frontend_redirect_url(result.token, redirect_target),
        status_code=302,
    )
    _clear_state_cookie(response)
    return response


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
