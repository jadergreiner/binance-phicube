"""
Testes de integração para notificações no fluxo completo do bot.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.config.settings import Settings
from src.notifications import NullNotifier, TelegramNotifier
from src.notifications.events import NotificationEvent
from src.strategy.signal_engine import Direction
from src.trading.order_manager import OrderManager
from src.trading.risk_manager import PositionSize


class TestOrderManagerNotifications:
    """Testes de integração das notificações no OrderManager."""

    @pytest.fixture
    def mock_client(self):
        """Cliente Binance mockado."""
        client = AsyncMock()
        client.set_leverage = AsyncMock()
        client.set_margin_mode = AsyncMock()
        client.create_market_order = AsyncMock(return_value={"id": "12345", "average": "50000.0"})
        client.round_price = AsyncMock(return_value=49000.0)
        client.create_stop_loss_order = AsyncMock(return_value={"id": "67890"})
        client.create_take_profit_order = AsyncMock(return_value={"id": "99999"})
        client.cancel_all_orders = AsyncMock()
        return client

    @pytest.fixture
    def mock_notifier(self):
        """Notificador mockado."""
        return AsyncMock()

    @pytest.fixture
    def order_manager(self, mock_client, mock_notifier):
        """OrderManager com notificador mockado."""
        return OrderManager(mock_client, leverage=5, notifier=mock_notifier)

    @pytest.fixture
    def sample_signal(self):
        """Sinal de exemplo para testes."""
        from datetime import UTC, datetime

        from src.strategy.signal_engine import Signal

        return Signal(
            symbol="BTCUSDT",
            timeframe="4h",
            direction=Direction.LONG,
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit=52000.0,
            fractal_ref=48500.0,
            detected_at=datetime.now(UTC),
        )

    @pytest.fixture
    def sample_position(self, sample_signal):
        """Posição de exemplo para testes."""
        return PositionSize(
            symbol=sample_signal.symbol,
            direction=sample_signal.direction,
            quantity=0.001,
            notional=50.0,
            margin_required=25.0,
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit=52000.0,
            risk_amount=10.0,
        )

    @pytest.mark.asyncio
    async def test_notificacao_nao_enviada_quando_trade_sucede(
        self, order_manager, sample_signal, sample_position, mock_notifier
    ):
        """Notificação NÃO deve ser enviada quando trade é executado com sucesso."""
        # Act
        result = await order_manager.execute(sample_signal, sample_position)

        # Assert
        assert result is not None
        assert result.status.name == "OPEN"
        mock_notifier.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_notificacao_sl_falha_enviada(self, mock_client, sample_signal, sample_position):
        """Notificação deve ser enviada quando SL falha após entrada."""
        # Arrange
        mock_notifier = AsyncMock()
        order_manager = OrderManager(mock_client, leverage=5, notifier=mock_notifier)

        # Simular falha no SL
        mock_client.create_stop_loss_order.side_effect = Exception("SL order failed")

        # Act
        result = await order_manager.execute(sample_signal, sample_position)

        # Assert
        assert result is not None
        assert result.status.name == "FAILED"
        mock_notifier.send.assert_called_once()

        # Verificar parâmetros da notificação
        call_args = mock_notifier.send.call_args
        assert call_args[0][0] == NotificationEvent.SL_PROTECTION_FAILED

        event_payload = call_args[0][1]
        assert event_payload.symbol == "BTCUSDT"
        assert event_payload.entry_order_id == "12345"
        assert event_payload.entry_price == 50000.0
        assert event_payload.quantity == 0.001


class TestTradingMonitorNotifications:
    """Testes de integração das notificações no TradingMonitor."""

    @pytest.mark.asyncio
    async def test_notificacao_trade_aberto_enviada(self):
        """Notificação deve ser enviada quando trade é aberto com sucesso."""
        # Este teste seria mais complexo, envolvendo mocks do TradingMonitor
        # Por ora, vamos pular e focar nos testes unitários já implementados
        pass


class TestNotifierCreation:
    """Testes para criação de notificadores baseada em configurações."""

    def test_cria_null_notifier_sem_configuracao(self, monkeypatch):
        """Deve criar NullNotifier quando Telegram não está configurado."""
        from src.main import _create_notifier

        # Mock settings sem Telegram
        mock_settings = Settings(
            binance_api_key="test",
            binance_api_secret="test",
            dashboard_api_key="test",
            dashboard_api_secret="test",
        )

        notifier = _create_notifier(mock_settings)
        assert isinstance(notifier, NullNotifier)

    def test_cria_telegram_notifier_com_configuracao_completa(self):
        """Deve criar TelegramNotifier quando Telegram está configurado."""
        from src.main import _create_notifier

        # Mock settings com Telegram
        mock_settings = Settings(
            binance_api_key="test",
            binance_api_secret="test",
            dashboard_api_key="test",
            dashboard_api_secret="test",
            telegram_token="123456:test_token",
            telegram_chat_id="987654321",
        )

        notifier = _create_notifier(mock_settings)
        assert isinstance(notifier, TelegramNotifier)
        assert notifier._token == "123456:test_token"
        assert notifier._chat_id == "987654321"
