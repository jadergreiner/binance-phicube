"""Testes do TradeCloseRouter — Mediator OrderMonitor ↔ RiskManager (SPEC_043)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.trading.trade_close_router import TradeCloseRouter


@pytest.fixture
def router() -> TradeCloseRouter:
    return TradeCloseRouter(
        portfolio_loss_threshold=2,
        portfolio_risk_reduction_factor=0.75,
    )


@pytest.mark.asyncio
async def test_router_registra_risk_manager(router: TradeCloseRouter) -> None:
    """TEST-043-19: register associa símbolo ao RiskManager."""
    rm = AsyncMock()
    router.register("BTCUSDT", rm)
    assert "BTCUSDT" in router._registry
    assert router._registry["BTCUSDT"] is rm


@pytest.mark.asyncio
async def test_router_rota_para_rm_correto(router: TradeCloseRouter) -> None:
    """TEST-043-20: __call__ roteia para o RiskManager do par."""
    rm = AsyncMock()
    router.register("BTCUSDT", rm)

    await router("BTCUSDT", 50.0)

    rm.register_trade_outcome.assert_awaited_once_with(50.0)


@pytest.mark.asyncio
async def test_router_rota_multiplos_pares(router: TradeCloseRouter) -> None:
    """TEST-043-21: Pares diferentes têm RMs independentes."""
    rm_btc = AsyncMock()
    rm_eth = AsyncMock()
    router.register("BTCUSDT", rm_btc)
    router.register("ETHUSDT", rm_eth)

    await router("BTCUSDT", 10.0)
    await router("ETHUSDT", -5.0)

    rm_btc.register_trade_outcome.assert_awaited_once_with(10.0)
    rm_eth.register_trade_outcome.assert_awaited_once_with(-5.0)


@pytest.mark.asyncio
async def test_router_symbol_inexistente_nao_crasha(router: TradeCloseRouter) -> None:
    """TEST-043-22: Symbol não registrado → log warning sem crash."""
    # Apenas registra BTC, chama com ETH
    rm = AsyncMock()
    router.register("BTCUSDT", rm)

    # Não deve levantar exceção
    await router("ETHUSDT", -10.0)

    rm.register_trade_outcome.assert_not_called()


@pytest.mark.asyncio
async def test_portfolio_cb_ativa_apos_duas_perdas(router: TradeCloseRouter) -> None:
    """TEST-043-23: Portfolio CB ativa após 2 perdas em pares diferentes."""
    rm_a = AsyncMock()
    rm_b = AsyncMock()
    router.register("BTCUSDT", rm_a)
    router.register("ETHUSDT", rm_b)

    assert not router.portfolio_breaker_active

    await router("BTCUSDT", -5.0)
    assert not router.portfolio_breaker_active
    assert router.portfolio_consecutive_losses == 1

    await router("ETHUSDT", -10.0)
    assert router.portfolio_breaker_active
    assert router.portfolio_consecutive_losses == 2


@pytest.mark.asyncio
async def test_portfolio_cb_reseta_com_vitoria(router: TradeCloseRouter) -> None:
    """TEST-043-24: Vitória no portfólio reseta o CB."""
    rm_a = AsyncMock()
    rm_b = AsyncMock()
    router.register("BTCUSDT", rm_a)
    router.register("ETHUSDT", rm_b)

    # 2 perdas → CB ativo
    await router("BTCUSDT", -5.0)
    await router("ETHUSDT", -10.0)
    assert router.portfolio_breaker_active

    # Vitória → reset
    await router("BTCUSDT", 20.0)
    assert not router.portfolio_breaker_active
    assert router.portfolio_consecutive_losses == 0


@pytest.mark.asyncio
async def test_portfolio_dead_zone_ignora_pnl_pequeno(router: TradeCloseRouter) -> None:
    """TEST-043-25 (D10): Portfolio CB ignora PnL ±0.001."""
    await router("BTCUSDT", 0.0005)
    assert router.portfolio_consecutive_losses == 0

    await router("ETHUSDT", -0.0005)
    assert router.portfolio_consecutive_losses == 0
    assert not router.portfolio_breaker_active


@pytest.mark.asyncio
async def test_portfolio_cb_vitoria_sem_estar_ativo_reseta_losses(
    router: TradeCloseRouter,
) -> None:
    """TEST-043-26: Vitória sem CB ativo zera contagem de perdas."""
    await router("BTCUSDT", -3.0)
    assert router.portfolio_consecutive_losses == 1

    await router("BTCUSDT", 5.0)
    assert router.portfolio_consecutive_losses == 0
    assert not router.portfolio_breaker_active


@pytest.mark.asyncio
async def test_portfolio_cb_nao_ativa_com_uma_perda(router: TradeCloseRouter) -> None:
    """TEST-043-27: Apenas 1 perda com threshold=2 não ativa CB."""
    await router("BTCUSDT", -5.0)
    assert not router.portfolio_breaker_active
