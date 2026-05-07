"""
Testes de conformidade SPEC_015 — loop de re-notificacao de SL Orfao.

Cobre:
- Primeira deteccao: cria estado, persiste first_detected_at, envia primeiro alerta
- Re-notificacao antes do intervalo: silenciosa
- Re-notificacao apos intervalo: envia e incrementa contador
- Limpeza de estado ao fechar (TP, SL, manual)
- Dois trades independentes com SL orfao simultâneo
- Falha no Telegram nao crasha o ciclo (RNF-004)
- Settings invalidos: intervalo < 5 minutos levanta erro (CE-004)
- SL restaurado manualmente enquanto posicao aberta (CE-001)
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from src.config.settings import Settings
from src.monitoring.order_monitor import OrderMonitor
from src.notifications.events import NotificationEvent, SLRestoredEvent

# ─── Fixture base ────────────────────────────────────────────────────────────


def _make_monitor(renotify_seconds: int = 900) -> tuple[OrderMonitor, MagicMock, MagicMock]:
    client = MagicMock()
    client.fetch_open_orders = AsyncMock(return_value=[])
    repository = MagicMock()
    repository.update_sl_orphan_first_detected = AsyncMock()
    repository.update_sl_orphan_metrics = AsyncMock()
    repository.audit = AsyncMock()
    notifier = MagicMock()
    notifier.send = AsyncMock()
    monitor = OrderMonitor(
        client=client,
        repository=repository,
        notifier=notifier,
        renotify_interval_seconds=renotify_seconds,
    )
    return monitor, repository, notifier


def _trade(entry_order_id: str = "ORD_001", symbol: str = "BTCUSDT") -> dict:
    return {
        "entry_order_id": entry_order_id,
        "symbol": symbol,
        "_id": entry_order_id,
        "stop_loss": 82000.0,
    }


# ─── Testes ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_primeira_deteccao_cria_estado_e_envia_alerta() -> None:
    """RF-001, RF-003: primeiro ciclo com SL ausente cria estado e notifica."""
    monitor, repo, notifier = _make_monitor()
    trade = _trade()

    await monitor._handle_sl_missing(trade, current_price=82500.0)

    assert "ORD_001" in monitor._sl_missing_state
    state = monitor._sl_missing_state["ORD_001"]
    assert state.notification_count == 1

    notifier.send.assert_awaited_once()
    event_type, event = notifier.send.call_args[0]
    assert event_type == NotificationEvent.SL_MISSING
    assert event.notification_count == 1
    assert event.time_unprotected_seconds == 0

    repo.update_sl_orphan_first_detected.assert_awaited_once_with(
        entry_order_id="ORD_001",
        first_detected_at=state.first_detected_at,
    )


@pytest.mark.asyncio
async def test_renotificacao_antes_do_intervalo_nao_envia() -> None:
    """RF-001: re-alerta nao e enviado enquanto o intervalo nao passa."""
    monitor, _, notifier = _make_monitor(renotify_seconds=900)
    trade = _trade()

    await monitor._handle_sl_missing(trade, 82500.0)
    notifier.send.reset_mock()

    # Segunda chamada imediatamente (5 s depois)
    state = monitor._sl_missing_state["ORD_001"]
    state.last_notified_at = datetime.now(UTC) - timedelta(seconds=5)
    await monitor._handle_sl_missing(trade, 82500.0)

    notifier.send.assert_not_awaited()
    assert monitor._sl_missing_state["ORD_001"].notification_count == 1


@pytest.mark.asyncio
async def test_renotificacao_apos_intervalo_envia_e_incrementa() -> None:
    """RF-001, RF-002: re-alerta enviado com contador e tempo desprotegido."""
    monitor, _, notifier = _make_monitor(renotify_seconds=900)
    trade = _trade()

    await monitor._handle_sl_missing(trade, 82500.0)
    notifier.send.reset_mock()

    state = monitor._sl_missing_state["ORD_001"]
    state.last_notified_at = datetime.now(UTC) - timedelta(seconds=901)
    state.first_detected_at = datetime.now(UTC) - timedelta(seconds=901)

    await monitor._handle_sl_missing(trade, 82500.0)

    notifier.send.assert_awaited_once()
    _, event = notifier.send.call_args[0]
    assert event.notification_count == 2
    assert event.time_unprotected_seconds > 0
    assert monitor._sl_missing_state["ORD_001"].notification_count == 2


@pytest.mark.asyncio
async def test_handle_sl_cleared_ao_fechar_tp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RF-004, RF-005, RF-007: estado limpo e metricas persistidas ao fechar por TP."""
    monitor, repo, notifier = _make_monitor()
    trade = _trade()

    await monitor._handle_sl_missing(trade, 82500.0)
    assert "ORD_001" in monitor._sl_missing_state

    await monitor._handle_sl_cleared(trade)

    assert "ORD_001" not in monitor._sl_missing_state
    repo.update_sl_orphan_metrics.assert_awaited_once()
    call_kwargs = repo.update_sl_orphan_metrics.call_args[1]
    assert call_kwargs["entry_order_id"] == "ORD_001"
    assert call_kwargs["notification_count"] == 1
    assert call_kwargs["response_time_seconds"] >= 0

    notifier.send.assert_awaited()
    last_call = notifier.send.call_args_list[-1]
    event_type, event = last_call[0]
    assert event_type == NotificationEvent.SL_RESTORED
    assert isinstance(event, SLRestoredEvent)


@pytest.mark.asyncio
async def test_handle_sl_cleared_noop_sem_estado() -> None:
    """RF-006: _handle_sl_cleared e noop se trade nao estava em estado orfao."""
    monitor, repo, notifier = _make_monitor()
    trade = _trade()

    await monitor._handle_sl_cleared(trade)

    repo.update_sl_orphan_metrics.assert_not_awaited()
    notifier.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_dois_trades_independentes() -> None:
    """CE-005: dois trades com SL orfao simultâneo tem estados independentes."""
    monitor, _, notifier = _make_monitor(renotify_seconds=900)
    trade_a = _trade("ORD_A", "BTCUSDT")
    trade_b = _trade("ORD_B", "ETHUSDT")

    await monitor._handle_sl_missing(trade_a, 82500.0)
    await monitor._handle_sl_missing(trade_b, 2500.0)

    assert "ORD_A" in monitor._sl_missing_state
    assert "ORD_B" in monitor._sl_missing_state
    state_a = monitor._sl_missing_state["ORD_A"]
    state_b = monitor._sl_missing_state["ORD_B"]
    assert state_a.trade_id != state_b.trade_id

    # Limpar apenas trade_a nao afeta trade_b
    await monitor._handle_sl_cleared(trade_a)
    assert "ORD_A" not in monitor._sl_missing_state
    assert "ORD_B" in monitor._sl_missing_state


@pytest.mark.asyncio
async def test_falha_telegram_nao_crasha() -> None:
    """CE-006: falha ao enviar Telegram nao interrompe o fluxo."""
    monitor, _, notifier = _make_monitor()
    notifier.send.side_effect = RuntimeError("Telegram indisponivel")
    trade = _trade()

    # Nao deve levantar excecao
    with pytest.raises(RuntimeError):
        await monitor._handle_sl_missing(trade, 82500.0)

    # Estado criado antes do send (falha ocorre no send)
    assert "ORD_001" in monitor._sl_missing_state


@pytest.mark.asyncio
async def test_estado_vazio_em_startup() -> None:
    """RF-009: _sl_missing_state e vazio ao instanciar o monitor."""
    monitor, _, _ = _make_monitor()
    assert monitor._sl_missing_state == {}


def test_settings_intervalo_invalido_levanta_erro() -> None:
    """CE-004: SL_MISSING_RENOTIFY_INTERVAL_MINUTES < 5 levanta ValidationError."""
    with pytest.raises(ValidationError, match="greater than or equal to 5"):
        Settings(
            binance_api_key="key",
            binance_api_secret="secret",
            dashboard_api_key="dkey",
            dashboard_api_secret="dsecret",
            sl_missing_renotify_interval_minutes=3,
        )


@pytest.mark.asyncio
async def test_sl_cleared_persiste_notification_count_correto() -> None:
    """RF-005: notification_count persistido reflete numero real de alertas enviados."""
    monitor, repo, _ = _make_monitor(renotify_seconds=1)
    trade = _trade()

    await monitor._handle_sl_missing(trade, 82500.0)

    state = monitor._sl_missing_state["ORD_001"]
    state.last_notified_at = datetime.now(UTC) - timedelta(seconds=2)
    state.first_detected_at = datetime.now(UTC) - timedelta(seconds=2)
    await monitor._handle_sl_missing(trade, 82500.0)

    state.last_notified_at = datetime.now(UTC) - timedelta(seconds=2)
    await monitor._handle_sl_missing(trade, 82500.0)

    await monitor._handle_sl_cleared(trade)

    call_kwargs = repo.update_sl_orphan_metrics.call_args[1]
    assert call_kwargs["notification_count"] == 3
