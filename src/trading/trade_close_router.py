"""TradeCloseRouter — Mediator entre OrderMonitor e RiskManager (SPEC_043).

Roteia eventos de fechamento de trade para o RiskManager correto (pair-level)
e mantém o circuit breaker de portfólio (portfolio-level).
"""

from __future__ import annotations

import asyncio
from typing import Any

from src.monitoring.logger import get_logger

logger = get_logger(__name__)

_DEAD_ZONE: float = 0.001  # D10: PnL abaixo deste valor não altera contadores


class TradeCloseRouter:
    """Mediator entre OrderMonitor (fechamento de trades) e RiskManagers.

    Responsabilidades:
    - Roteia chamadas __call__(symbol, pnl_usdt) para o RiskManager do par.
    - Mantém circuit breaker de portfólio (threshold=2, reduction=0.75).
    """

    def __init__(
        self,
        portfolio_loss_threshold: int = 2,
        portfolio_risk_reduction_factor: float = 0.75,
    ) -> None:
        # Mapeamento symbol → RiskManager
        self._registry: dict[str, Any] = {}

        # Portfolio-level state
        self._portfolio_consecutive_losses: int = 0
        self._portfolio_breaker_active: bool = False
        self._portfolio_loss_threshold = portfolio_loss_threshold
        self._portfolio_risk_reduction_factor = portfolio_risk_reduction_factor
        self._portfolio_lock: asyncio.Lock = asyncio.Lock()

    def register(self, symbol: str, risk_manager: Any) -> None:
        """Registra um RiskManager para um símbolo."""
        self._registry[symbol.upper()] = risk_manager
        logger.debug(
            "trade_close_router_registered",
            symbol=symbol.upper(),
        )

    @property
    def portfolio_breaker_active(self) -> bool:
        """Indica se o circuit breaker de portfólio está ativo."""
        return self._portfolio_breaker_active

    @property
    def portfolio_consecutive_losses(self) -> int:
        """Número de perdas consecutivas no portfólio."""
        return self._portfolio_consecutive_losses

    async def __call__(self, symbol: str, pnl_usdt: float) -> None:
        """Roteia um trade fechado para o RiskManager do par.

        Args:
            symbol: Símbolo do par (ex: BTCUSDT).
            pnl_usdt: PnL realizado do trade fechado.
        """
        symbol_up = symbol.upper()

        # Pair-level
        rm = self._registry.get(symbol_up)
        if rm is not None:
            await rm.register_trade_outcome(pnl_usdt)
        else:
            logger.warning(
                "trade_close_router_no_registered_rm",
                symbol=symbol_up,
            )

        # Portfolio-level
        await self._update_portfolio(pnl_usdt)

    async def _update_portfolio(self, pnl_usdt: float) -> None:
        """Atualiza o circuit breaker de portfólio (PRD D04).

        Threshold: 2 perdas em pares diferentes.
        Reduction: 0.75 (redução adicional sobre todos os pares).
        Zona morta: ±0.001 (D10).
        """
        if abs(pnl_usdt) <= _DEAD_ZONE:
            return

        async with self._portfolio_lock:
            if pnl_usdt > 0:
                # Vitória no portfólio → reset
                if self._portfolio_breaker_active:
                    self._portfolio_consecutive_losses = 0
                    self._portfolio_breaker_active = False
                    logger.info(
                        "portfolio_circuit_breaker_reset",
                        reason="portfolio_win",
                    )
                else:
                    self._portfolio_consecutive_losses = 0
            else:
                # Perda no portfólio
                self._portfolio_consecutive_losses += 1
                if (self._portfolio_consecutive_losses >= self._portfolio_loss_threshold
                        and not self._portfolio_breaker_active):
                    self._portfolio_breaker_active = True
                    logger.warning(
                        "portfolio_circuit_breaker_activated",
                        consecutive_losses=self._portfolio_consecutive_losses,
                        threshold=self._portfolio_loss_threshold,
                        reduction_factor=self._portfolio_risk_reduction_factor,
                    )
