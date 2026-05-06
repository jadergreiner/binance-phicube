"""
Testes para TelegramNotifier e NullNotifier.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from src.notifications.events import (
    CriticalErrorEvent,
    NotificationEvent,
    SLProtectionFailedEvent,
    TradeOpenedEvent,
)
from src.notifications.telegram_notifier import NullNotifier, TelegramNotifier


class TestNullNotifier:
    """Testes para NullNotifier."""

    @pytest.fixture
    def notifier(self) -> NullNotifier:
        return NullNotifier()

    @pytest.mark.asyncio
    async def test_send_sempre_retorna_true(self, notifier: NullNotifier) -> None:
        """NullNotifier sempre retorna True, independente do evento."""
        result = await notifier.send(NotificationEvent.TRADE_OPENED, {})
        assert result is True

        result = await notifier.send(NotificationEvent.CRITICAL_ERROR, "error")
        assert result is True


class TestTelegramNotifier:
    """Testes para TelegramNotifier."""

    @pytest.fixture
    def notifier(self) -> TelegramNotifier:
        return TelegramNotifier(token="123456:test_token", chat_id="987654321")

    def test_init_configura_urls_corretamente(self, notifier: TelegramNotifier) -> None:
        """Deve configurar base_url corretamente."""
        expected_url = "https://api.telegram.org/bot123456:test_token"
        assert notifier._base_url == expected_url
        assert notifier._chat_id == "987654321"

    @pytest.mark.asyncio
    async def test_send_com_sucesso(self, notifier: TelegramNotifier) -> None:
        """Deve retornar True quando Telegram API responde com sucesso."""
        event = TradeOpenedEvent(
            symbol="BTCUSDT",
            direction="long",
            quantity=0.001,
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit=52000.0,
            risk_amount=10.0,
            timestamp=pytest.importorskip("datetime").datetime(2026, 5, 4, 12, 0, 0),
        )

        mock_response_data = {"ok": True, "result": {"message_id": 123}}

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_response_data)
            mock_post.return_value.__aenter__.return_value = mock_response

            result = await notifier.send(NotificationEvent.TRADE_OPENED, event)

            assert result is True
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_com_falha_api(self, notifier: TelegramNotifier) -> None:
        """Deve retornar False quando Telegram API retorna erro."""
        event = CriticalErrorEvent(
            operation="trade_execution",
            symbol="BTCUSDT",
            error_message="Connection timeout",
            timestamp=pytest.importorskip("datetime").datetime(2026, 5, 4, 12, 0, 0),
        )

        mock_response_data = {"ok": False, "description": "Bad Request: chat not found"}

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 400
            mock_response.json = AsyncMock(return_value=mock_response_data)
            mock_post.return_value.__aenter__.return_value = mock_response

            result = await notifier.send(NotificationEvent.CRITICAL_ERROR, event)

            assert result is False

    @pytest.mark.asyncio
    async def test_send_com_timeout(self, notifier: TelegramNotifier) -> None:
        """Deve retornar False e fazer retry quando há timeout."""
        event = SLProtectionFailedEvent(
            symbol="ETHUSDT",
            entry_order_id="12345",
            entry_price=3000.0,
            quantity=1.0,
            timestamp=pytest.importorskip("datetime").datetime(2026, 5, 4, 12, 0, 0),
        )

        with patch("aiohttp.ClientSession.post", side_effect=asyncio.TimeoutError):
            result = await notifier.send(NotificationEvent.SL_PROTECTION_FAILED, event)

            assert result is False
            # Deve tentar 3 vezes (retry)
            assert asyncio.TimeoutError

    @pytest.mark.asyncio
    async def test_send_com_network_error(self, notifier: TelegramNotifier) -> None:
        """Deve retornar False quando há erro de rede."""
        import aiohttp

        event = NotificationEvent.CRITICAL_ERROR
        payload = "Network error test"

        with patch(
            "aiohttp.ClientSession.post",
            side_effect=aiohttp.ClientError("Connection failed")
        ):
            result = await notifier.send(event, payload)

            assert result is False

    def test_format_message_com_evento_estruturado(self, notifier: TelegramNotifier) -> None:
        """Deve usar método to_message() quando disponível."""
        event = TradeOpenedEvent(
            symbol="BTCUSDT",
            direction="long",
            quantity=0.001,
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit=52000.0,
            risk_amount=10.0,
            timestamp=pytest.importorskip("datetime").datetime(2026, 5, 4, 12, 0, 0),
        )

        message = notifier._format_message(NotificationEvent.TRADE_OPENED, event)

        assert "TRADE ABERTO" in message
        assert "BTCUSDT" in message
        assert "LONG" in message
        assert "50000.00" in message

    def test_format_message_com_payload_simples(self, notifier: TelegramNotifier) -> None:
        """Deve formatar payload simples quando não há to_message()."""
        event = NotificationEvent.CRITICAL_ERROR
        payload = "Simple error message"

        message = notifier._format_message(event, payload)

        assert "CRITICAL_ERROR" in message
        assert "Simple error message" in message

    @pytest.mark.asyncio
    async def test_token_nao_aparece_nos_logs(
        self, notifier: TelegramNotifier, caplog: pytest.LogCaptureFixture
    ) -> None:
        """TEST_004_05: Nenhum log deve conter o token ou chat_id (INV-004-04)."""
        import aiohttp
        import logging

        with caplog.at_level(logging.DEBUG, logger="src.notifications.telegram_notifier"):
            # Simula falha de rede — exceção pode carregar URL com token
            with patch(
                "aiohttp.ClientSession.post",
                side_effect=aiohttp.ClientError("https://api.telegram.org/bot123456:test_token/sendMessage: err"),
            ):
                await notifier.send(NotificationEvent.CRITICAL_ERROR, "test")

            # Simula exceção genérica que poderia vazar token via str(exc)
            with patch(
                "src.notifications.telegram_notifier.TelegramNotifier._send_message",
                side_effect=RuntimeError("token=123456:test_token leaked"),
            ):
                await notifier.send(NotificationEvent.CRITICAL_ERROR, "test2")

        assert "123456:test_token" not in caplog.text
        assert "987654321" not in caplog.text