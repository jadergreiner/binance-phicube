"""Testes unitários do dataclass Trade — campos RF-11 (SPEC_006 task_001)."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.strategy.signal_engine import Direction
from src.trading.order_manager import Trade, TradeStatus


def _make_trade(**kwargs) -> Trade:
    defaults = dict(
        symbol="BTCUSDT",
        timeframe="4h",
        direction=Direction.LONG,
        quantity=0.001,
        entry_price=50000.0,
        stop_loss=49000.0,
        take_profit=52000.0,
        risk_amount=10.0,
        margin_used=100.0,
        entry_order_id="ord_001",
    )
    defaults.update(kwargs)
    return Trade(**defaults)


class TestTradeModelRF11:
    """TEST_006_01 e TEST_006_02 — campos RF-11 no dataclass Trade."""

    def test_novos_campos_existem_com_default_none(self) -> None:
        trade = _make_trade()
        assert trade.exit_price is None
        assert trade.pnl_usdt is None
        assert trade.close_reason is None

    def test_to_dict_inclui_novos_campos(self) -> None:
        trade = _make_trade()
        d = trade.to_dict()
        assert "exit_price" in d
        assert "pnl_usdt" in d
        assert "close_reason" in d

    def test_trade_tp_close_reason(self) -> None:
        """TEST_006_01: trade fechado por TP tem close_reason='TP' e pnl_usdt>0."""
        trade = _make_trade(
            status=TradeStatus.CLOSED_TP,
            exit_price=52000.0,
            pnl_usdt=20.0,
            close_reason="TP",
            closed_at=datetime.now(UTC),
        )
        assert trade.close_reason == "TP"
        assert trade.pnl_usdt > 0
        assert trade.exit_price == 52000.0
        d = trade.to_dict()
        assert d["close_reason"] == "TP"
        assert d["pnl_usdt"] == 20.0
        assert d["exit_price"] == 52000.0

    def test_trade_sl_close_reason(self) -> None:
        """TEST_006_02: trade fechado por SL tem close_reason='SL' e pnl_usdt<0."""
        trade = _make_trade(
            status=TradeStatus.CLOSED_SL,
            exit_price=49000.0,
            pnl_usdt=-10.0,
            close_reason="SL",
            closed_at=datetime.now(UTC),
        )
        assert trade.close_reason == "SL"
        assert trade.pnl_usdt < 0
        d = trade.to_dict()
        assert d["close_reason"] == "SL"
        assert d["pnl_usdt"] == -10.0

    def test_trade_manual_close_reason(self) -> None:
        trade = _make_trade(
            status=TradeStatus.CLOSED_MANUAL,
            exit_price=51000.0,
            pnl_usdt=5.0,
            close_reason="manual",
            closed_at=datetime.now(UTC),
        )
        assert trade.close_reason == "manual"
        d = trade.to_dict()
        assert d["close_reason"] == "manual"

    def test_campos_antigos_inalterados(self) -> None:
        """Retrocompatibilidade: campos existentes continuam funcionando."""
        trade = _make_trade(pnl=15.0)
        assert trade.pnl == 15.0
        assert trade.to_dict()["pnl"] == 15.0
