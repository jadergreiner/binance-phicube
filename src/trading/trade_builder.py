"""
TradeBuilder — Builder Pattern para construção imutável de Trade.

Permite construção passo a passo com validação incremental,
substituindo a construção manual verbosa em OrderManager.execute().
"""

from __future__ import annotations

from typing import Any, Self

from src.config.settings import ExitStrategy
from src.strategy.signal_engine import Direction, Signal
from src.trading.risk_manager import PositionSize


class TradeBuilderError(Exception):
    """Levantada quando validação do TradeBuilder falha."""


class TradeBuilder:
    """Construtor fluente e validado para objetos Trade.

    Uso:
        trade = (
            TradeBuilder()
            .with_entry(signal, position)
            .with_orders(entry_order_id, sl_order_id, tp_order_ids)
            .with_exit_strategy(exit_strategy, tp_levels)
            .build()
        )
    """

    def __init__(self) -> None:
        from src.trading.order_manager import TradeStatus

        self._symbol: str | None = None
        self._timeframe: str | None = None
        self._direction: Direction | None = None
        self._quantity: float | None = None
        self._entry_price: float | None = None
        self._stop_loss: float | None = None
        self._take_profit: float | None = None
        self._risk_amount: float | None = None
        self._margin_used: float | None = None
        self._entry_order_id: str | None = None
        self._sl_order_id: str | None = None
        self._tp_order_id: str | None = None
        self._status = TradeStatus.OPEN
        self._signal: dict[str, Any] = {}
        self._exit_strategy: ExitStrategy | None = None
        self._tp_levels: list[dict[str, float]] | None = None
        self._tp_order_ids: list[str] | None = None

    def with_entry(self, signal: Signal, position: PositionSize) -> Self:
        """Preenche campos derivados do sinal e do position sizing."""
        self._symbol = signal.symbol
        self._timeframe = signal.timeframe
        self._direction = signal.direction
        self._entry_price = position.entry_price
        self._stop_loss = position.stop_loss
        self._take_profit = position.take_profit
        self._quantity = position.quantity
        self._risk_amount = position.risk_amount
        self._margin_used = position.margin_required
        self._signal = signal.to_dict()
        return self

    def with_orders(
        self,
        entry_order_id: str,
        sl_order_id: str | None,
        tp_order_ids: list[str] | None,
    ) -> Self:
        """Preenche IDs das ordens criadas na exchange."""
        self._entry_order_id = entry_order_id
        self._sl_order_id = sl_order_id
        if tp_order_ids:
            self._tp_order_ids = tp_order_ids
            self._tp_order_id = tp_order_ids[0] if tp_order_ids else None
        return self

    def with_exit_strategy(
        self,
        strategy: ExitStrategy,
        tp_levels: list[dict[str, float]] | None,
    ) -> Self:
        """Configura estratégia de saída e níveis de TP parcial."""
        self._exit_strategy = strategy
        self._tp_levels = tp_levels
        return self

    def with_status(self, status) -> Self:
        """Define status do trade (default: OPEN)."""
        self._status = status
        return self

    def _validate(self) -> None:
        """Valida campos obrigatórios antes de construir o Trade."""
        if not self._symbol:
            raise TradeBuilderError("symbol is required")
        if not self._timeframe:
            raise TradeBuilderError("timeframe is required")
        if self._direction is None:
            raise TradeBuilderError("direction is required")
        if self._entry_price is None or self._entry_price <= 0:
            raise TradeBuilderError("entry_price must be > 0")
        if self._quantity is None or self._quantity <= 0:
            raise TradeBuilderError("quantity must be > 0")
        if self._stop_loss is None or self._take_profit is None:
            raise TradeBuilderError("stop_loss and take_profit are required")
        if self._stop_loss == self._take_profit:
            raise TradeBuilderError("stop_loss and take_profit must differ")
        if not self._entry_order_id:
            raise TradeBuilderError("entry_order_id is required")

    def build(self):
        """Constrói e retorna o Trade imutável."""
        from src.trading.order_manager import Trade

        self._validate()

        # _validate() garante que campos obrigatórios não são None
        assert self._symbol is not None
        assert self._timeframe is not None
        assert self._direction is not None
        assert self._entry_price is not None
        assert self._quantity is not None
        assert self._stop_loss is not None
        assert self._take_profit is not None
        assert self._entry_order_id is not None

        return Trade(
            symbol=self._symbol,
            timeframe=self._timeframe,
            direction=self._direction,
            quantity=self._quantity,
            entry_price=self._entry_price,
            stop_loss=self._stop_loss,
            take_profit=self._take_profit,
            risk_amount=self._risk_amount or 0.0,
            margin_used=self._margin_used or 0.0,
            entry_order_id=self._entry_order_id,
            sl_order_id=self._sl_order_id,
            tp_order_id=self._tp_order_id,
            status=self._status,
            signal=self._signal,
            exit_strategy=self._exit_strategy,
            tp_levels=self._tp_levels,
            tp_order_ids=self._tp_order_ids,
        )

    def build_failed(
        self,
        signal: Signal,
        position: PositionSize,
        entry_order_id: str,
    ):
        """Constrói um Trade com status FAILED (para rollback ou erro)."""
        from src.trading.order_manager import Trade, TradeStatus

        return Trade(
            symbol=signal.symbol,
            timeframe=signal.timeframe,
            direction=signal.direction,
            quantity=position.quantity,
            entry_price=position.entry_price,
            stop_loss=position.stop_loss,
            take_profit=position.take_profit,
            risk_amount=position.risk_amount,
            margin_used=position.margin_required,
            entry_order_id=entry_order_id,
            status=TradeStatus.FAILED,
            signal=signal.to_dict(),
        )
