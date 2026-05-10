"""Testes da rota MCP-PoS /customers (SPEC-driven)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.customers import router
from src.config.mcp_pos import mcp_serena_context


def _make_app(repo=None) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    if repo is not None:
        app.state.repository = repo
    return app


class TestListCustomers:
    def test_retorna_200_com_lista_de_clientes(self) -> None:
        customers = [
            {
                "id": "1",
                "name": "João Silva",
                "email": "joao@email.com",
                "phone": "11999999999",
                "document": "123.456.789-00",
                "status": "active",
                "notes": None,
                "created_at": datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
                "updated_at": datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
            }
        ]
        repo = AsyncMock()
        repo.list_customers = AsyncMock(return_value=customers)
        repo.count_customers = AsyncMock(return_value=1)

        app = _make_app(repo=repo)
        with TestClient(app) as client:
            response = client.get("/customers")

        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == 1
        assert len(payload["customers"]) == 1
        assert payload["customers"][0]["name"] == "João Silva"
        assert payload["customers"][0]["email"] == "joao@email.com"
        assert payload["customers"][0]["created_at"].endswith("Z")
        assert payload["customers"][0]["created_at_br"] == "01/05/2026 09:00:00"
        assert payload["mcp_serena_context"] == mcp_serena_context
        assert payload["timezone"] == "America/Sao_Paulo"
        repo.list_customers.assert_awaited_once_with(limit=50, skip=0)
        repo.count_customers.assert_awaited_once()

    def test_retorna_200_com_array_vazio(self) -> None:
        repo = AsyncMock()
        repo.list_customers = AsyncMock(return_value=[])
        repo.count_customers = AsyncMock(return_value=0)

        app = _make_app(repo=repo)
        with TestClient(app) as client:
            response = client.get("/customers")

        assert response.status_code == 200
        assert response.json()["customers"] == []
        assert response.json()["total"] == 0

    def test_respeita_limit_e_skip(self) -> None:
        repo = AsyncMock()
        repo.list_customers = AsyncMock(return_value=[])
        repo.count_customers = AsyncMock(return_value=0)

        app = _make_app(repo=repo)
        with TestClient(app) as client:
            response = client.get("/customers?limit=10&skip=5")

        assert response.status_code == 200
        payload = response.json()
        assert payload["limit"] == 10
        assert payload["skip"] == 5
        repo.list_customers.assert_awaited_once_with(limit=10, skip=5)

    def test_retorna_503_sem_repositorio(self) -> None:
        app = _make_app(repo=None)
        with TestClient(app) as client:
            response = client.get("/customers")

        assert response.status_code == 503
        assert response.json() == {"detail": "Repositório indisponível"}

    def test_retorna_503_quando_repositorio_falha(self) -> None:
        repo = AsyncMock()
        repo.list_customers = AsyncMock(side_effect=RuntimeError("db down"))

        app = _make_app(repo=repo)
        with TestClient(app) as client:
            response = client.get("/customers")

        assert response.status_code == 503
        assert response.json() == {"detail": "Repositório indisponível"}


class TestGetCustomer:
    def test_retorna_200_com_cliente(self) -> None:
        customer = {
            "id": "abc123",
            "name": "Maria Souza",
            "email": "maria@email.com",
            "phone": None,
            "document": None,
            "status": "active",
            "notes": "Cliente VIP",
            "created_at": datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
            "updated_at": datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
        }
        repo = AsyncMock()
        repo.get_customer = AsyncMock(return_value=customer)

        app = _make_app(repo=repo)
        with TestClient(app) as client:
            response = client.get("/customers/abc123")

        assert response.status_code == 200
        payload = response.json()
        assert payload["customer"]["name"] == "Maria Souza"
        assert payload["customer"]["notes"] == "Cliente VIP"
        assert payload["mcp_serena_context"] == mcp_serena_context
        repo.get_customer.assert_awaited_once_with("abc123")

    def test_retorna_404_quando_nao_encontrado(self) -> None:
        repo = AsyncMock()
        repo.get_customer = AsyncMock(return_value=None)

        app = _make_app(repo=repo)
        with TestClient(app) as client:
            response = client.get("/customers/inexistente")

        assert response.status_code == 404
        assert response.json() == {"detail": "Cliente não encontrado"}

    def test_retorna_503_sem_repositorio(self) -> None:
        app = _make_app(repo=None)
        with TestClient(app) as client:
            response = client.get("/customers/abc123")

        assert response.status_code == 503

    def test_retorna_503_quando_repositorio_falha(self) -> None:
        repo = AsyncMock()
        repo.get_customer = AsyncMock(side_effect=RuntimeError("db down"))

        app = _make_app(repo=repo)
        with TestClient(app) as client:
            response = client.get("/customers/abc123")

        assert response.status_code == 503


class TestCreateCustomer:
    def test_retorna_201_com_cliente_criado(self) -> None:
        repo = AsyncMock()
        repo.create_customer = AsyncMock(return_value="new-id-123")

        app = _make_app(repo=repo)
        with TestClient(app) as client:
            response = client.post(
                "/customers",
                json={"name": "Novo Cliente", "email": "novo@email.com"},
            )

        assert response.status_code == 201
        payload = response.json()
        assert payload["id"] == "new-id-123"
        assert payload["customer"]["name"] == "Novo Cliente"
        assert payload["customer"]["email"] == "novo@email.com"
        assert payload["customer"]["status"] == "active"
        assert payload["mcp_serena_context"] == mcp_serena_context
        repo.create_customer.assert_awaited_once()

    def test_retorna_422_quando_name_ausente(self) -> None:
        repo = AsyncMock()

        app = _make_app(repo=repo)
        with TestClient(app) as client:
            response = client.post("/customers", json={"email": "sem@nome.com"})

        assert response.status_code == 422
        assert response.json() == {"detail": "Campo 'name' é obrigatório"}

    def test_retorna_400_quando_json_invalido(self) -> None:
        repo = AsyncMock()

        app = _make_app(repo=repo)
        with TestClient(app) as client:
            response = client.post(
                "/customers", content=b"not json", headers={"content-type": "application/json"}
            )

        assert response.status_code == 400

    def test_retorna_503_sem_repositorio(self) -> None:
        app = _make_app(repo=None)
        with TestClient(app) as client:
            response = client.post("/customers", json={"name": "Teste"})

        assert response.status_code == 503


class TestUpdateCustomer:
    def test_retorna_200_com_cliente_atualizado(self) -> None:
        repo = AsyncMock()
        repo.update_customer = AsyncMock(return_value=True)
        repo.get_customer = AsyncMock(
            return_value={
                "id": "abc123",
                "name": "Atualizado",
                "email": None,
                "phone": None,
                "document": None,
                "status": "inactive",
                "notes": None,
                "created_at": datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
                "updated_at": datetime(2026, 5, 1, 13, 0, tzinfo=UTC),
            }
        )

        app = _make_app(repo=repo)
        with TestClient(app) as client:
            response = client.put(
                "/customers/abc123",
                json={"name": "Atualizado", "status": "inactive"},
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["customer"]["name"] == "Atualizado"
        assert payload["customer"]["status"] == "inactive"
        assert payload["mcp_serena_context"] == mcp_serena_context
        repo.update_customer.assert_awaited_once_with(
            "abc123", {"name": "Atualizado", "status": "inactive"}
        )

    def test_retorna_404_quando_nao_encontrado(self) -> None:
        repo = AsyncMock()
        repo.update_customer = AsyncMock(return_value=False)

        app = _make_app(repo=repo)
        with TestClient(app) as client:
            response = client.put("/customers/inexistente", json={"name": "X"})

        assert response.status_code == 404
        assert response.json() == {"detail": "Cliente não encontrado"}

    def test_retorna_422_quando_sem_campos(self) -> None:
        repo = AsyncMock()

        app = _make_app(repo=repo)
        with TestClient(app) as client:
            response = client.put("/customers/abc123", json={})

        assert response.status_code == 422
        assert response.json() == {"detail": "Nenhum campo para atualizar"}

    def test_retorna_503_sem_repositorio(self) -> None:
        app = _make_app(repo=None)
        with TestClient(app) as client:
            response = client.put("/customers/abc123", json={"name": "X"})

        assert response.status_code == 503


class TestDeleteCustomer:
    def test_retorna_200_com_cliente_removido(self) -> None:
        repo = AsyncMock()
        repo.delete_customer = AsyncMock(return_value=True)

        app = _make_app(repo=repo)
        with TestClient(app) as client:
            response = client.delete("/customers/abc123")

        assert response.status_code == 200
        assert response.json()["detail"] == "Cliente removido"
        assert response.json()["mcp_serena_context"] == mcp_serena_context
        repo.delete_customer.assert_awaited_once_with("abc123")

    def test_retorna_404_quando_nao_encontrado(self) -> None:
        repo = AsyncMock()
        repo.delete_customer = AsyncMock(return_value=False)

        app = _make_app(repo=repo)
        with TestClient(app) as client:
            response = client.delete("/customers/inexistente")

        assert response.status_code == 404
        assert response.json() == {"detail": "Cliente não encontrado"}

    def test_retorna_503_sem_repositorio(self) -> None:
        app = _make_app(repo=None)
        with TestClient(app) as client:
            response = client.delete("/customers/abc123")

        assert response.status_code == 503
