"""Rotas MCP-PoS de clientes para o dashboard."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.api.datetime_utils import (
    BRAZIL_TIMEZONE,
    to_brazil_datetime_str,
    to_iso8601_utc,
)
from src.config.mcp_pos import Customer, mcp_serena_context

router = APIRouter()


def _customer_to_response(customer: dict[str, Any]) -> dict[str, Any]:
    created = customer.get("created_at")
    updated = customer.get("updated_at")
    return {
        "id": customer.get("id"),
        "name": customer.get("name"),
        "email": customer.get("email"),
        "phone": customer.get("phone"),
        "document": customer.get("document"),
        "status": customer.get("status"),
        "notes": customer.get("notes"),
        "created_at": to_iso8601_utc(created),
        "created_at_br": to_brazil_datetime_str(created),
        "updated_at": to_iso8601_utc(updated),
        "updated_at_br": to_brazil_datetime_str(updated),
    }


@router.get("/customers")
async def list_customers(
    request: Request,
    limit: int = 50,
    skip: int = 0,
) -> JSONResponse:
    repo = getattr(request.app.state, "repository", None)
    if repo is None:
        return JSONResponse(status_code=503, content={"detail": "Repositório indisponível"})

    try:
        customers = await repo.list_customers(limit=limit, skip=skip)
        total = await repo.count_customers()
    except Exception:
        return JSONResponse(status_code=503, content={"detail": "Repositório indisponível"})

    payload = [_customer_to_response(c) for c in customers]
    generated_at = to_iso8601_utc(datetime.now(UTC))
    ctx = dict(mcp_serena_context)
    return JSONResponse(
        status_code=200,
        content={
            "customers": payload,
            "total": total,
            "limit": limit,
            "skip": skip,
            "generated_at": generated_at,
            "generated_at_br": to_brazil_datetime_str(generated_at),
            "timezone": BRAZIL_TIMEZONE,
            "mcp_serena_context": ctx,
        },
    )


@router.get("/customers/{customer_id}")
async def get_customer(request: Request, customer_id: str) -> JSONResponse:
    repo = getattr(request.app.state, "repository", None)
    if repo is None:
        return JSONResponse(status_code=503, content={"detail": "Repositório indisponível"})

    try:
        customer = await repo.get_customer(customer_id)
    except Exception:
        return JSONResponse(status_code=503, content={"detail": "Repositório indisponível"})

    if customer is None:
        return JSONResponse(status_code=404, content={"detail": "Cliente não encontrado"})

    generated_at = to_iso8601_utc(datetime.now(UTC))
    ctx = dict(mcp_serena_context)
    return JSONResponse(
        status_code=200,
        content={
            "customer": _customer_to_response(customer),
            "generated_at": generated_at,
            "generated_at_br": to_brazil_datetime_str(generated_at),
            "timezone": BRAZIL_TIMEZONE,
            "mcp_serena_context": ctx,
        },
    )


@router.post("/customers")
async def create_customer(request: Request) -> JSONResponse:
    repo = getattr(request.app.state, "repository", None)
    if repo is None:
        return JSONResponse(status_code=503, content={"detail": "Repositório indisponível"})

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"detail": "JSON inválido"})

    name = (body.get("name") or "").strip()
    if not name:
        return JSONResponse(status_code=422, content={"detail": "Campo 'name' é obrigatório"})

    now = datetime.now(UTC)
    customer = Customer(
        id=body.get("id", str(now.timestamp())),
        name=name,
        email=body.get("email"),
        phone=body.get("phone"),
        document=body.get("document"),
        status=body.get("status", "active"),
        notes=body.get("notes"),
        created_at=now,
        updated_at=now,
    )

    try:
        doc_id = await repo.create_customer(customer.to_dict())
    except Exception:
        return JSONResponse(status_code=503, content={"detail": "Repositório indisponível"})

    generated_at = to_iso8601_utc(now)
    ctx = dict(mcp_serena_context)
    return JSONResponse(
        status_code=201,
        content={
            "id": doc_id,
            "customer": _customer_to_response(customer.to_dict()),
            "generated_at": generated_at,
            "generated_at_br": to_brazil_datetime_str(generated_at),
            "timezone": BRAZIL_TIMEZONE,
            "mcp_serena_context": ctx,
        },
    )


@router.put("/customers/{customer_id}")
async def update_customer(request: Request, customer_id: str) -> JSONResponse:
    repo = getattr(request.app.state, "repository", None)
    if repo is None:
        return JSONResponse(status_code=503, content={"detail": "Repositório indisponível"})

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"detail": "JSON inválido"})

    update: dict[str, Any] = {}
    for field in ("name", "email", "phone", "document", "status", "notes"):
        if field in body:
            update[field] = body[field]

    if not update:
        return JSONResponse(status_code=422, content={"detail": "Nenhum campo para atualizar"})

    try:
        updated = await repo.update_customer(customer_id, update)
    except Exception:
        return JSONResponse(status_code=503, content={"detail": "Repositório indisponível"})

    if not updated:
        return JSONResponse(status_code=404, content={"detail": "Cliente não encontrado"})

    customer = await repo.get_customer(customer_id)
    generated_at = to_iso8601_utc(datetime.now(UTC))
    ctx = dict(mcp_serena_context)
    return JSONResponse(
        status_code=200,
        content={
            "customer": _customer_to_response(customer) if customer else None,
            "generated_at": generated_at,
            "generated_at_br": to_brazil_datetime_str(generated_at),
            "timezone": BRAZIL_TIMEZONE,
            "mcp_serena_context": ctx,
        },
    )


@router.delete("/customers/{customer_id}")
async def delete_customer(request: Request, customer_id: str) -> JSONResponse:
    repo = getattr(request.app.state, "repository", None)
    if repo is None:
        return JSONResponse(status_code=503, content={"detail": "Repositório indisponível"})

    try:
        deleted = await repo.delete_customer(customer_id)
    except Exception:
        return JSONResponse(status_code=503, content={"detail": "Repositório indisponível"})

    if not deleted:
        return JSONResponse(status_code=404, content={"detail": "Cliente não encontrado"})

    generated_at = to_iso8601_utc(datetime.now(UTC))
    ctx = dict(mcp_serena_context)
    return JSONResponse(
        status_code=200,
        content={
            "detail": "Cliente removido",
            "generated_at": generated_at,
            "generated_at_br": to_brazil_datetime_str(generated_at),
            "timezone": BRAZIL_TIMEZONE,
            "mcp_serena_context": ctx,
        },
    )
