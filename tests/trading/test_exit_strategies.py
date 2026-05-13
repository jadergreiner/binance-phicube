"""
Testes de conformidade SPEC_030 — Estratégias de saída (TP Parcial).

Cobre:
- TEST_030_01: TP parcial 2 níveis
- TEST_030_02: TP parcial 3 níveis
- TEST_030_03: exit_strategy="fixed" (sem regressão)
- TEST_030_04: SL nunca movido (DD-002)
- TEST_030_05: Rollback se TP parcial falha (P-004)
- TEST_030_06: RRR médio ponderado (D-007)
- TEST_030_07: Trade.to_dict() serializa novos campos
- TEST_030_08: Settings validation rejeita tp_levels inválidos
- TEST_030_09: SimulatedClient + TP parcial integrado
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import ValidationError

from src.config.settings import ExitStrategy
from src.exchange.simulated_client import SimulatedBinanceClient
from src.strategy.signal_engine import Direction, Signal
from src.trading.order_manager import OrderManager, Trade, TradeStatus
from src.trading.risk_manager import PositionSize


def _sample_signal() -> Signal:
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


def _sample_position() -> PositionSize:
    return PositionSize(
        symbol="BTCUSDT",
        direction=Direction.LONG,
        quantity=0.001,
        notional=50.0,
        margin_required=25.0,
        entry_price=50000.0,
        stop_loss=49000.0,
        take_profit=52000.0,
        risk_amount=10.0,
    )


def _mock_client() -> AsyncMock:
    """Cria um mock de cliente Binance para testes de exit strategy.

    round_price e round_quantity usam Mock comum (não async) porque
    são métodos síncronos na interface do cliente.
    """
    client = AsyncMock()
    client.set_leverage = AsyncMock()
    client.set_margin_mode = AsyncMock()
    client.create_market_order = AsyncMock(return_value={"id": "entry-1", "average": "50000.0"})
    client.round_price = Mock(side_effect=lambda s, p: p)
    client.round_quantity = Mock(side_effect=lambda s, q: q)
    client.create_stop_loss_order = AsyncMock(return_value={"id": "sl-1"})
    client.create_take_profit_order = AsyncMock(return_value={"id": "tp-1"})
    client.cancel_all_orders = AsyncMock()
    return client


# ═══════════════════════════════════════════════════════════════════════════════
# TEST_030_01: TP parcial 2 níveis — posição reduz, SL permanece
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_partial_tp_two_levels() -> None:
    client = _mock_client()
    client.create_take_profit_order = AsyncMock(
        side_effect=[
            {"id": "tp-1"},
            {"id": "tp-2"},
        ]
    )
    manager = OrderManager(
        client=client,
        leverage=5,
        exit_strategy=ExitStrategy.PARTIAL,
        tp_levels=[
            {"qty_pct": 50.0, "price_distance_pct": 2.0},
            {"qty_pct": 50.0, "price_distance_pct": 4.0},
        ],
    )

    trade = await manager.execute(_sample_signal(), _sample_position())

    assert trade is not None
    assert trade.status == TradeStatus.OPEN
    assert client.create_take_profit_order.call_count == 2
    assert trade.exit_strategy == ExitStrategy.PARTIAL
    assert trade.tp_levels is not None
    assert len(trade.tp_levels) == 2
    assert trade.tp_order_ids == ["tp-1", "tp-2"]


# ═══════════════════════════════════════════════════════════════════════════════
# TEST_030_02: TP parcial 3 níveis — execução sequencial
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_partial_tp_three_levels() -> None:
    client = _mock_client()
    client.create_take_profit_order = AsyncMock(
        side_effect=[
            {"id": "tp-1"},
            {"id": "tp-2"},
            {"id": "tp-3"},
        ]
    )
    manager = OrderManager(
        client=client,
        leverage=5,
        exit_strategy=ExitStrategy.PARTIAL,
        tp_levels=[
            {"qty_pct": 40.0, "price_distance_pct": 2.0},
            {"qty_pct": 30.0, "price_distance_pct": 4.0},
            {"qty_pct": 30.0, "price_distance_pct": 6.0},
        ],
    )

    trade = await manager.execute(_sample_signal(), _sample_position())

    assert trade is not None
    assert trade.status == TradeStatus.OPEN
    assert client.create_take_profit_order.call_count == 3
    assert trade.tp_order_ids is not None
    assert len(trade.tp_order_ids) == 3
    assert trade.tp_order_ids == ["tp-1", "tp-2", "tp-3"]


# ═══════════════════════════════════════════════════════════════════════════════
# TEST_030_03: exit_strategy="fixed" → comportamento atual (sem regressão)
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_fixed_strategy_no_regression() -> None:
    client = _mock_client()
    manager = OrderManager(client=client, leverage=5)

    trade = await manager.execute(_sample_signal(), _sample_position())

    assert trade is not None
    assert trade.status == TradeStatus.OPEN
    assert client.create_take_profit_order.call_count == 1
    assert trade.exit_strategy == ExitStrategy.FIXED
    assert trade.tp_order_ids is not None
    assert len(trade.tp_order_ids) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# TEST_030_04: SL nunca movido (DD-002)
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_sl_uses_full_quantity_partial_tp() -> None:
    client = _mock_client()
    client.create_take_profit_order = AsyncMock(
        side_effect=[
            {"id": "tp-1"},
            {"id": "tp-2"},
        ]
    )
    manager = OrderManager(
        client=client,
        leverage=5,
        exit_strategy=ExitStrategy.PARTIAL,
        tp_levels=[
            {"qty_pct": 50.0, "price_distance_pct": 2.0},
            {"qty_pct": 50.0, "price_distance_pct": 4.0},
        ],
    )

    trade = await manager.execute(_sample_signal(), _sample_position())

    assert trade is not None
    assert trade.status == TradeStatus.OPEN
    # SL must be placed for the FULL position quantity, not partial TP qty
    client.create_stop_loss_order.assert_called_once_with(
        symbol="BTCUSDT",
        side="sell",
        quantity=0.001,
        stop_price=49000.0,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST_030_05: Rollback total se TP parcial falha no meio (P-004)
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_rollback_when_partial_tp_fails() -> None:
    client = _mock_client()
    client.create_take_profit_order = AsyncMock(
        side_effect=[
            {"id": "tp-1"},
            Exception("Second TP failed"),
        ]
    )
    manager = OrderManager(
        client=client,
        leverage=5,
        exit_strategy=ExitStrategy.PARTIAL,
        tp_levels=[
            {"qty_pct": 50.0, "price_distance_pct": 2.0},
            {"qty_pct": 50.0, "price_distance_pct": 4.0},
        ],
    )

    trade = await manager.execute(_sample_signal(), _sample_position())

    assert trade is not None
    assert trade.status == TradeStatus.FAILED
    # Command Pattern: rollback chama cancel_all_orders para cada comando executado
    # (MarketOrder + StopLoss + TakeProfit1 = 3 chamadas)
    assert client.cancel_all_orders.call_count == 3
    assert client.cancel_all_orders.call_args_list[-1] == (("BTCUSDT",),)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST_030_06: RRR médio ponderado (D-007)
# ═══════════════════════════════════════════════════════════════════════════════


def test_calc_rrr_weighted() -> None:
    entry = 50000.0
    sl = 49000.0  # 2% distance
    tp_levels = [
        {"qty_pct": 50.0, "price_distance_pct": 2.0},
        {"qty_pct": 50.0, "price_distance_pct": 4.0},
    ]
    rrr = OrderManager._calc_rrr_weighted(entry, sl, tp_levels, Direction.LONG)
    # (2/2)*0.5 + (4/2)*0.5 = 0.5 + 1.0 = 1.5
    assert rrr == 1.5


# ═══════════════════════════════════════════════════════════════════════════════
# TEST_030_07: Trade.to_dict() serializa novos campos
# ═══════════════════════════════════════════════════════════════════════════════


def test_trade_to_dict_includes_exit_fields() -> None:
    """Trade com exit_strategy, tp_levels e tp_order_ids deve serializar tudo."""
    trade = Trade(
        symbol="BTCUSDT",
        timeframe="4h",
        direction=Direction.LONG,
        quantity=0.001,
        entry_price=50000.0,
        stop_loss=49000.0,
        take_profit=52000.0,
        risk_amount=10.0,
        margin_used=25.0,
        entry_order_id="entry-1",
        sl_order_id="sl-1",
        tp_order_id="tp-1",
        exit_strategy=ExitStrategy.PARTIAL,
        tp_levels=[{"qty_pct": 50.0, "price_distance_pct": 2.0}],
        tp_order_ids=["tp-1"],
    )

    d = trade.to_dict()
    assert d["exit_strategy"] == "partial"
    assert d["tp_levels"] == [{"qty_pct": 50.0, "price_distance_pct": 2.0}]
    assert d["tp_order_ids"] == ["tp-1"]


def test_trade_to_dict_exit_fields_none_when_unset() -> None:
    """Trade sem os novos campos (backward compat) deve retornar None."""
    trade = Trade(
        symbol="BTCUSDT",
        timeframe="4h",
        direction=Direction.LONG,
        quantity=0.001,
        entry_price=50000.0,
        stop_loss=49000.0,
        take_profit=52000.0,
        risk_amount=10.0,
        margin_used=25.0,
        entry_order_id="entry-1",
    )

    d = trade.to_dict()
    assert d["exit_strategy"] is None
    assert d["tp_levels"] is None
    assert d["tp_order_ids"] is None


# ═══════════════════════════════════════════════════════════════════════════════
# TEST_030_08: Settings validation rejeita tp_levels inválidos
# ═══════════════════════════════════════════════════════════════════════════════


def _make_settings(**kwargs):
    """Helper para criar Settings com credenciais mínimas."""
    from src.config.settings import Settings

    base = dict(
        binance_api_key="test",
        binance_api_secret="test",
        dashboard_api_key="test",
        dashboard_api_secret="test",
    )
    base.update(kwargs)
    return Settings(**base)


def test_settings_rejects_tp_levels_sum_over_100() -> None:
    with pytest.raises(ValidationError, match="deve ser <= 100"):
        _make_settings(
            tp_levels=[
                {"qty_pct": 60.0, "price_distance_pct": 2.0},
                {"qty_pct": 50.0, "price_distance_pct": 4.0},
            ]
        )


def test_settings_rejects_empty_tp_levels() -> None:
    with pytest.raises(ValidationError, match="entre 1 e 3"):
        _make_settings(tp_levels=[])


def test_settings_rejects_negative_qty_pct() -> None:
    with pytest.raises(ValidationError, match="deve ser > 0"):
        _make_settings(
            tp_levels=[
                {"qty_pct": -10.0, "price_distance_pct": 2.0},
            ]
        )


def test_settings_accepts_pct_alias() -> None:
    """Adapter: chave `pct` é aceita e normalizada para `price_distance_pct`.

    O operador pode usar `pct` (conforme documentado na SPEC e PRD)
    e o sistema normaliza automaticamente para o campo canônico.
    Sem esta normalização, o OrderManager quebra com KeyError.
    """
    s = _make_settings(
        exit_strategy="partial",
        tp_levels=[
            {"qty_pct": 50.0, "pct": 2.0},
            {"qty_pct": 50.0, "pct": 4.0},
        ],
    )
    # Verifica que `pct` foi normalizado para `price_distance_pct`
    assert s.tp_levels[0]["price_distance_pct"] == 2.0
    assert s.tp_levels[1]["price_distance_pct"] == 4.0
    # Verifica que a chave `pct` foi removida
    assert "pct" not in s.tp_levels[0]
    assert "pct" not in s.tp_levels[1]


def test_settings_accepts_mixed_pct_and_canonical() -> None:
    """Adapter: níveis mistos (alguns com `pct`, outros com `price_distance_pct`) são aceitos.

    `price_distance_pct` canônico tem precedência se ambos existirem.
    """
    s = _make_settings(
        exit_strategy="partial",
        tp_levels=[
            {"qty_pct": 50.0, "pct": 2.0},
            {"qty_pct": 50.0, "price_distance_pct": 4.0},
        ],
    )
    assert s.tp_levels[0]["price_distance_pct"] == 2.0
    assert s.tp_levels[1]["price_distance_pct"] == 4.0
    assert "pct" not in s.tp_levels[0]
    assert "pct" not in s.tp_levels[1]


# ═══════════════════════════════════════════════════════════════════════════════
# TEST_030_09: SimulatedClient + TP parcial integrado
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_simulated_client_partial_tp() -> None:
    real_client = AsyncMock()
    real_client.connect = AsyncMock()
    real_client.fetch_ticker = AsyncMock(return_value={"last": 50000.0, "close": 50000.0})
    real_client.fetch_usdt_balance = AsyncMock(return_value=0.0)
    real_client.round_price = Mock(side_effect=lambda s, p: p)
    real_client.round_quantity = Mock(side_effect=lambda s, q: q)

    sim = SimulatedBinanceClient(real_client=real_client, initial_balance_usdt=10000)
    await sim.connect()
    await sim.set_leverage("BTCUSDT", 5)
    await sim.set_margin_mode("BTCUSDT", "isolated")

    manager = OrderManager(
        client=sim,
        leverage=5,
        exit_strategy=ExitStrategy.PARTIAL,
        tp_levels=[
            {"qty_pct": 50.0, "price_distance_pct": 2.0},
            {"qty_pct": 50.0, "price_distance_pct": 4.0},
        ],
    )

    trade = await manager.execute(_sample_signal(), _sample_position())
    assert trade is not None
    assert trade.status == TradeStatus.OPEN

    # Deve ter 1 SL + 2 TP = 3 ordens condicionais abertas
    open_orders = await sim.fetch_open_orders("BTCUSDT")
    assert len(open_orders) == 3

    # O SimulatedBinanceClient aplica 0.02% de slippage no entry,
    # então o fill real é ~50010. Os TPs ficam em ~51010 e ~52010.
    # Usamos preços ligeiramente acima para garantir ativação correta.
    tp_orders = [o for o in open_orders if o.get("type") == "TAKE_PROFIT_MARKET"]
    tp_prices = sorted([float(o.get("stopPrice", 0)) for o in tp_orders])

    # Executa primeiro TP
    executed = await sim.check_and_execute_conditional_orders("BTCUSDT", tp_prices[0] + 1.0)
    assert len(executed) == 1  # Apenas TP1 deve disparar

    # Executa segundo TP
    executed = await sim.check_and_execute_conditional_orders("BTCUSDT", tp_prices[1] + 1.0)
    assert len(executed) == 1  # TP2 deve disparar

    # Verifica que SL permanece aberto (posição reduzida, mas SL intacto)
    remaining = await sim.fetch_open_orders("BTCUSDT")
    assert len(remaining) == 1  # Apenas o SL


# ═══════════════════════════════════════════════════════════════════════════════
# TEST_030_10: Trailing Stop — cria trailing order em vez de SL fixo (V2-01)
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_trailing_stop_creates_trailing_order() -> None:
    """Trailing Stop: deve chamar create_trailing_stop_order e NÃO criar TP fixo."""
    client = _mock_client()
    client.create_trailing_stop_order = AsyncMock(return_value={"id": "trail-1"})

    manager = OrderManager(
        client=client,
        leverage=5,
        exit_strategy=ExitStrategy.TRAILING,
        trailing_activation_pct=2.0,
        trailing_callback_rate=0.5,
    )

    trade = await manager.execute(_sample_signal(), _sample_position())

    assert trade is not None
    assert trade.status == TradeStatus.OPEN
    client.create_trailing_stop_order.assert_called_once()
    client.create_take_profit_order.assert_not_called()
    assert trade.exit_strategy == ExitStrategy.TRAILING


# ═══════════════════════════════════════════════════════════════════════════════
# TEST_030_11: Trailing Stop — rollback se criação falha (V2-02)
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_trailing_stop_rollback_on_failure() -> None:
    """Trailing Stop: quando create_trailing_stop_order falha, deve cancelar
    todas as ordens e marcar trade como FAILED."""
    client = _mock_client()
    client.create_trailing_stop_order = AsyncMock(
        side_effect=Exception("Trailing failed"),
    )

    manager = OrderManager(
        client=client,
        leverage=5,
        exit_strategy=ExitStrategy.TRAILING,
    )

    trade = await manager.execute(_sample_signal(), _sample_position())

    assert trade is not None
    assert trade.status == TradeStatus.FAILED
    client.cancel_all_orders.assert_called_once_with("BTCUSDT")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST_030_12: Settings validation — trailing activation > callback_rate (V2-03)
# ═══════════════════════════════════════════════════════════════════════════════


def test_settings_trailing_validation() -> None:
    """Settings deve validar que trailing_activation_pct > trailing_callback_rate."""
    # Valid: activation > callback
    s = _make_settings(
        exit_strategy="trailing",
        trailing_activation_pct=2.0,
        trailing_callback_rate=1.0,
    )
    assert s.trailing_activation_pct == 2.0
    assert s.trailing_callback_rate == 1.0

    # Invalid: activation <= callback → deve levantar ValidationError
    with pytest.raises(ValidationError):
        _make_settings(
            exit_strategy="trailing",
            trailing_activation_pct=0.5,
            trailing_callback_rate=1.0,
        )
