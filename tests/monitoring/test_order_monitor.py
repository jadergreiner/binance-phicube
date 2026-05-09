"""
Testes para OrderMonitor — SPEC_012.

Cobre os 13 cenários obrigatórios:
    TEST_012_01: SL cancelado → notificação critical
    TEST_012_02: sem notificação duplicada
    TEST_012_03: TP executado → PnL correto no MongoDB
    TEST_012_04: SL executado → PnL correto no MongoDB
    TEST_012_05: fechamento manual → cancel_all + CLOSED_MANUAL + is_estimated=True
    TEST_012_06: fetch_order retry (NetworkError → sucesso no retry)
    TEST_012_07: fetch_order esgota retries → log warning, aguarda próximo ciclo
    TEST_012_08: falha em um símbolo não afeta outros
    TEST_012_09: startup reconciliation (trade OPEN com SL preenchido)
    TEST_012_10: shutdown gracioso (CancelledError)
    TEST_012_11: PnL com fees
    TEST_012_12: PnL sem fees
    TEST_012_13: slippage no SL (exit_price = average, não stop_price)
"""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import ccxt.async_support as ccxt
import pytest

from src.monitoring.order_monitor import OrderMonitor
from src.notifications.events import NotificationEvent, SLMissingEvent
from src.trading.order_manager import TradeStatus


def _make_trade(
    *,
    symbol: str = "BTCUSDT",
    direction: str = "long",
    entry_price: float = 40000.0,
    stop_loss: float = 39000.0,
    take_profit: float = 42000.0,
    quantity: float = 0.01,
    sl_order_id: str = "sl-001",
    tp_order_id: str = "tp-001",
    entry_order_id: str = "entry-001",
    fees: float = 0.0,
) -> dict:
    """Cria um trade OPEN de teste com valores padrão."""
    return {
        "_id": "mongo-id-001",
        "symbol": symbol,
        "direction": direction,
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "quantity": quantity,
        "sl_order_id": sl_order_id,
        "tp_order_id": tp_order_id,
        "entry_order_id": entry_order_id,
        "status": "OPEN",
        "fees": fees,
        "opened_at": datetime.now(UTC),
    }


def _make_order(*, status: str, average: float, stop_price: float = 0.0) -> dict:
    """Cria um objeto de ordem ccxt simplificado."""
    return {
        "status": status,
        "average": average,
        "price": average,
        "stopPrice": stop_price,
    }


def _make_monitor(
    *,
    get_open_trades: list | None = None,
    fetch_order_side_effect=None,
    fetch_positions: list | None = None,
    fetch_ticker_price: float = 40500.0,
) -> tuple[OrderMonitor, AsyncMock, AsyncMock, AsyncMock]:
    """Cria OrderMonitor com mocks configurados.

    Retorna: (monitor, mock_client, mock_repo, mock_notifier)
    """
    mock_client = MagicMock()
    mock_repo = MagicMock()
    mock_notifier = MagicMock()

    # Configurar retornos padrão
    mock_repo.get_open_trades = AsyncMock(return_value=get_open_trades or [])
    mock_repo.update_trade_status = AsyncMock()
    mock_repo.audit = AsyncMock()

    # Simular acesso à coleção trades para is_estimated
    trades_collection = MagicMock()
    trades_collection.update_one = AsyncMock()
    db_mock = MagicMock()
    db_mock.__getitem__ = MagicMock(return_value=trades_collection)
    mock_repo.database = db_mock

    mock_client.fetch_ticker = AsyncMock(
        return_value={"last": fetch_ticker_price, "close": fetch_ticker_price}
    )
    mock_client.cancel_all_orders = AsyncMock()
    mock_client.fetch_open_positions = AsyncMock(return_value=fetch_positions or [])

    if fetch_order_side_effect is not None:
        mock_client.fetch_order = AsyncMock(side_effect=fetch_order_side_effect)
    else:
        mock_client.fetch_order = AsyncMock(return_value=_make_order(status="open", average=0.0))

    mock_notifier.send = AsyncMock(return_value=True)

    monitor = OrderMonitor(
        client=mock_client,
        repository=mock_repo,
        notifier=mock_notifier,
        interval_seconds=60,
    )

    return monitor, mock_client, mock_repo, mock_notifier


# ─── TEST_012_01: SL cancelado → notificação critical ────────────────────────


@pytest.mark.asyncio
async def test_012_01_sl_cancelado_notificacao_critical():
    """SL com status=canceled e posição aberta deve gerar notificação SL_MISSING."""
    trade = _make_trade()

    # SL cancelado, TP ainda aberto
    def _fetch_order_side_effect(order_id, symbol):
        if order_id == "sl-001":
            return _make_order(status="canceled", average=0.0).__class__.__init__  # noqa
        return _make_order(status="open", average=0.0)

    monitor, mock_client, mock_repo, mock_notifier = _make_monitor(
        get_open_trades=[trade],
        fetch_positions=[{"symbol": "BTCUSDT", "contracts": 0.01}],
    )

    # SL cancelado
    mock_client.fetch_order = AsyncMock(
        side_effect=lambda order_id, symbol: _make_order(status="canceled", average=0.0)
        if order_id == "sl-001"
        else _make_order(status="open", average=0.0)
    )

    await monitor._check_trade(trade)

    mock_notifier.send.assert_called_once()
    event_type, payload = mock_notifier.send.call_args[0]
    assert event_type == NotificationEvent.SL_MISSING
    assert isinstance(payload, SLMissingEvent)
    assert payload.symbol == "BTCUSDT"
    assert payload.sl_price == 39000.0
    assert payload.current_price == pytest.approx(40500.0, rel=1e-3)


# ─── TEST_012_02: sem notificação duplicada ───────────────────────────────────


@pytest.mark.asyncio
async def test_012_02_sem_notificacao_duplicada():
    """Guard deve impedir segunda notificação de SL_MISSING para o mesmo trade."""
    trade = _make_trade()

    monitor, mock_client, mock_repo, mock_notifier = _make_monitor(
        get_open_trades=[trade],
        fetch_positions=[{"symbol": "BTCUSDT", "contracts": 0.01}],
    )

    mock_client.fetch_order = AsyncMock(return_value=_make_order(status="canceled", average=0.0))

    # Primeiro ciclo — deve notificar
    await monitor._check_trade(trade)
    assert mock_notifier.send.call_count == 1

    # Segundo ciclo — NÃO deve notificar novamente
    await monitor._check_trade(trade)
    assert mock_notifier.send.call_count == 1  # sem nova chamada


# ─── TEST_012_03: TP executado → PnL correto no MongoDB ──────────────────────


@pytest.mark.asyncio
async def test_012_03_tp_executado_pnl_correto():
    """TP executado deve atualizar MongoDB com status CLOSED_TP e PnL calculado."""
    trade = _make_trade(
        direction="long",
        entry_price=40000.0,
        quantity=0.01,
        fees=0.0,
    )

    # SL ainda aberto, TP fechado com average=42000
    monitor, mock_client, mock_repo, mock_notifier = _make_monitor(
        get_open_trades=[trade],
    )

    mock_client.fetch_order = AsyncMock(
        side_effect=lambda order_id, symbol: _make_order(status="open", average=0.0)
        if order_id == "sl-001"
        else _make_order(status="closed", average=42000.0)
    )

    await monitor._check_trade(trade)

    mock_repo.update_trade_status.assert_called_once()
    call_kwargs = mock_repo.update_trade_status.call_args.kwargs
    assert call_kwargs["status"] == TradeStatus.CLOSED_TP
    assert call_kwargs["exit_price"] == pytest.approx(42000.0)
    # PnL: (42000 - 40000) * 0.01 * 1 - 0 = 20.0
    assert call_kwargs["pnl_usdt"] == pytest.approx(20.0)
    assert call_kwargs["close_reason"] == "tp_executed"


# ─── TEST_012_04: SL executado → PnL correto no MongoDB ──────────────────────


@pytest.mark.asyncio
async def test_012_04_sl_executado_pnl_correto():
    """SL executado deve atualizar MongoDB com status CLOSED_SL e PnL calculado."""
    trade = _make_trade(
        direction="long",
        entry_price=40000.0,
        quantity=0.01,
        fees=0.0,
    )

    # SL fechado com average=39100
    monitor, mock_client, mock_repo, mock_notifier = _make_monitor(
        get_open_trades=[trade],
    )

    mock_client.fetch_order = AsyncMock(return_value=_make_order(status="closed", average=39100.0))

    await monitor._check_trade(trade)

    call_kwargs = mock_repo.update_trade_status.call_args.kwargs
    assert call_kwargs["status"] == TradeStatus.CLOSED_SL
    assert call_kwargs["exit_price"] == pytest.approx(39100.0)
    # PnL: (39100 - 40000) * 0.01 * 1 - 0 = -9.0
    assert call_kwargs["pnl_usdt"] == pytest.approx(-9.0)
    assert call_kwargs["close_reason"] == "sl_executed"


# ─── TEST_012_05: fechamento manual ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_012_05_fechamento_manual_cancel_all_closed_manual_is_estimated():
    """Fechamento manual deve cancelar ordens e registrar CLOSED_MANUAL com is_estimated=True."""
    trade = _make_trade()

    monitor, mock_client, mock_repo, mock_notifier = _make_monitor(
        get_open_trades=[trade],
        # Nenhuma posição aberta na exchange
        fetch_positions=[],
        fetch_ticker_price=40200.0,
    )

    # SL e TP ainda abertos — posição zerada manualmente
    mock_client.fetch_order = AsyncMock(return_value=_make_order(status="open", average=0.0))

    await monitor._check_trade(trade)
    # 1º ciclo: apenas pendência de confirmação
    mock_repo.update_trade_status.assert_not_called()

    await monitor._check_trade(trade)

    # Deve cancelar todas as ordens
    mock_client.cancel_all_orders.assert_called_once_with("BTCUSDT")

    # Status = CLOSED_MANUAL
    call_kwargs = mock_repo.update_trade_status.call_args.kwargs
    assert call_kwargs["status"] == TradeStatus.CLOSED_MANUAL
    assert call_kwargs["close_reason"] == "manual_close"

    # is_estimated = True deve ser setado no documento
    trades_col = mock_repo.database["trades"]
    trades_col.update_one.assert_called_once()
    update_arg = trades_col.update_one.call_args[0][1]
    assert update_arg["$set"]["is_estimated"] is True


# ─── TEST_012_06: fetch_order retry (NetworkError → sucesso no retry) ─────────


@pytest.mark.asyncio
async def test_012_06_fetch_order_retry_network_error_sucesso():
    """fetch_order deve fazer retry em NetworkError e retornar o resultado no retry."""
    monitor, mock_client, _, _ = _make_monitor()

    sucesso = _make_order(status="open", average=0.0)

    chamadas = 0

    async def _fetch_order_com_falha(order_id, symbol):
        nonlocal chamadas
        chamadas += 1
        if chamadas == 1:
            raise ccxt.NetworkError("timeout")
        return sucesso

    mock_client.fetch_order = _fetch_order_com_falha

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await monitor._fetch_order_with_retry("order-001", "BTCUSDT")

    assert result == sucesso
    assert chamadas == 2  # 1 falha + 1 sucesso


# ─── TEST_012_07: fetch_order esgota retries → log warning ───────────────────


@pytest.mark.asyncio
async def test_012_07_fetch_order_esgota_retries_retorna_none():
    """Após esgotar todos os retries, _fetch_order_with_retry deve retornar None."""
    monitor, mock_client, _, _ = _make_monitor()

    mock_client.fetch_order = AsyncMock(side_effect=ccxt.NetworkError("timeout"))

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await monitor._fetch_order_with_retry("order-001", "BTCUSDT", retries=3)

    assert result is None
    assert mock_client.fetch_order.call_count == 3


@pytest.mark.asyncio
async def test_012_07b_order_not_found_nao_aborta_e_permite_fechamento_manual():
    """OrderNotFound não deve fechar no 1º ciclo; fecha após confirmação em 2 ciclos."""
    trade = _make_trade()

    monitor, mock_client, mock_repo, _ = _make_monitor(
        get_open_trades=[trade],
        fetch_positions=[],
        fetch_ticker_price=40200.0,
    )

    mock_client.fetch_order = AsyncMock(side_effect=ccxt.OrderNotFound("missing"))

    await monitor._check_trade(trade)
    mock_repo.update_trade_status.assert_not_called()

    await monitor._check_trade(trade)

    call_kwargs = mock_repo.update_trade_status.call_args.kwargs
    assert call_kwargs["status"] == TradeStatus.CLOSED_MANUAL
    assert call_kwargs["close_reason"] == "manual_close"


@pytest.mark.asyncio
async def test_012_07c_order_not_found_com_posicao_aberta_mantem_trade_open():
    """OrderNotFound com posição ainda aberta não pode fechar trade manualmente."""
    trade = _make_trade(symbol="ATOMUSDT")

    monitor, mock_client, mock_repo, _ = _make_monitor(
        get_open_trades=[trade],
        fetch_positions=[{"symbol": "ATOM/USDT:USDT", "contracts": 1.0}],
        fetch_ticker_price=1.90,
    )
    mock_client.fetch_order = AsyncMock(side_effect=ccxt.OrderNotFound("missing"))

    await monitor._check_trade(trade)
    await monitor._check_trade(trade)

    mock_repo.update_trade_status.assert_not_called()


def test_012_14_normaliza_simbolos_equivalentes():
    monitor, _, _, _ = _make_monitor()
    assert monitor._normalize_symbol("ATOMUSDT") == monitor._normalize_symbol("ATOM/USDT:USDT")


# ─── TEST_012_08: falha em um símbolo não afeta outros ───────────────────────


@pytest.mark.asyncio
async def test_012_08_falha_um_simbolo_nao_afeta_outros():
    """Exceção em _check_trade de um trade não deve impedir verificação dos outros."""
    trade_a = _make_trade(symbol="BTCUSDT", entry_order_id="entry-a", sl_order_id="sl-a")
    trade_b = _make_trade(symbol="ETHUSDT", entry_order_id="entry-b", sl_order_id="sl-b")

    monitor, mock_client, mock_repo, _ = _make_monitor(
        get_open_trades=[trade_a, trade_b],
    )

    chamadas = []

    async def _fetch_order_seletivo(order_id, symbol):
        chamadas.append(symbol)
        if symbol == "BTCUSDT":
            raise RuntimeError("falha simulada no BTCUSDT")
        return _make_order(status="open", average=0.0)

    mock_client.fetch_order = _fetch_order_seletivo
    mock_client.fetch_open_positions = AsyncMock(return_value=[])

    # Não deve propagar exceção
    await monitor._check_all_open_trades()

    # ETHUSDT deve ter sido verificado mesmo com erro no BTCUSDT
    assert "ETHUSDT" in chamadas


# ─── TEST_012_09: startup reconciliation ─────────────────────────────────────


@pytest.mark.asyncio
async def test_012_09_startup_reconciliation_trade_open_sl_preenchido():
    """Trade OPEN com SL aberto ao iniciar deve permanecer sem alteração de status."""
    trade = _make_trade()

    monitor, mock_client, mock_repo, mock_notifier = _make_monitor(
        get_open_trades=[trade],
        fetch_positions=[{"symbol": "BTCUSDT", "contracts": 0.01}],
    )

    # SL e TP abertos (estado normal)
    mock_client.fetch_order = AsyncMock(return_value=_make_order(status="open", average=0.0))

    await monitor._check_trade(trade)

    # Nenhuma atualização de status
    mock_repo.update_trade_status.assert_not_called()
    # Nenhuma notificação
    mock_notifier.send.assert_not_called()


# ─── TEST_012_10: shutdown gracioso (CancelledError) ─────────────────────────


@pytest.mark.asyncio
async def test_012_10_shutdown_gracioso_cancelled_error():
    """run() deve encerrar graciosamente ao receber CancelledError."""
    import asyncio as _asyncio

    monitor, mock_client, mock_repo, _ = _make_monitor(get_open_trades=[])

    async def _sleep_que_cancela(seconds):
        raise _asyncio.CancelledError()

    with patch("asyncio.sleep", side_effect=_sleep_que_cancela):
        # Não deve propagar CancelledError nem levantar exceção
        await monitor.run()

    # Chegou aqui sem erro — shutdown gracioso confirmado


# ─── TEST_012_11: PnL com fees ────────────────────────────────────────────────


def test_012_11_pnl_com_fees():
    """PnL deve deduzir fees do resultado."""
    monitor, _, _, _ = _make_monitor()
    trade = _make_trade(
        direction="long",
        entry_price=40000.0,
        quantity=0.01,
        fees=2.0,
    )
    pnl = monitor._calc_pnl(trade, exit_price=42000.0)
    # (42000 - 40000) * 0.01 * 1 - 2.0 = 20.0 - 2.0 = 18.0
    assert pnl == pytest.approx(18.0)


# ─── TEST_012_12: PnL sem fees ───────────────────────────────────────────────


def test_012_12_pnl_sem_fees():
    """PnL sem fees deve ser calculado corretamente para LONG e SHORT."""
    monitor, _, _, _ = _make_monitor()

    # LONG
    trade_long = _make_trade(direction="long", entry_price=40000.0, quantity=0.01)
    pnl_long = monitor._calc_pnl(trade_long, exit_price=42000.0)
    assert pnl_long == pytest.approx(20.0)

    # SHORT
    trade_short = _make_trade(direction="short", entry_price=40000.0, quantity=0.01)
    pnl_short = monitor._calc_pnl(trade_short, exit_price=38000.0)
    # (38000 - 40000) * 0.01 * (-1) - 0 = (-20) * (-1) = 20.0
    assert pnl_short == pytest.approx(20.0)

    # SHORT com loss
    pnl_short_loss = monitor._calc_pnl(trade_short, exit_price=42000.0)
    # (42000 - 40000) * 0.01 * (-1) = 20.0 * (-1) = -20.0
    assert pnl_short_loss == pytest.approx(-20.0)


# ─── TEST_012_13: slippage no SL (exit_price = average, não stop_price) ───────


@pytest.mark.asyncio
async def test_012_13_slippage_sl_exit_price_usa_average():
    """exit_price do SL deve ser o campo `average` (execução real), não stopPrice."""
    trade = _make_trade(
        direction="long",
        entry_price=40000.0,
        quantity=0.01,
        stop_loss=39000.0,
        fees=0.0,
    )

    monitor, mock_client, mock_repo, _ = _make_monitor(get_open_trades=[trade])

    # stopPrice = 39000, mas average = 38950 (slippage de 50 USDT)
    sl_order = _make_order(status="closed", average=38950.0, stop_price=39000.0)
    mock_client.fetch_order = AsyncMock(return_value=sl_order)

    await monitor._check_trade(trade)

    call_kwargs = mock_repo.update_trade_status.call_args.kwargs
    # exit_price deve ser average (38950), não stopPrice (39000)
    assert call_kwargs["exit_price"] == pytest.approx(38950.0)
    # PnL: (38950 - 40000) * 0.01 * 1 - 0 = -10.5
    assert call_kwargs["pnl_usdt"] == pytest.approx(-10.5)
