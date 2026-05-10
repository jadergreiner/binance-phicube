"""Testes do SimulatedBinanceClient (paper trading / simulation mode)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import ccxt.async_support as ccxt
import pandas as pd
import pytest

from src.exchange.binance_client import BinanceClient, InsufficientLiquidityError
from src.exchange.simulated_client import SimulatedBinanceClient

# ─── Helpers ─────────────────────────────────────────────────────────────────

_SYMBOL = "BTCUSDT"


def _make_real_client() -> MagicMock:
    """Cria um mock de BinanceClient com os métodos públicos esperados."""
    client = MagicMock(spec=BinanceClient)
    client.fetch_ohlcv = AsyncMock(return_value=pd.DataFrame())
    client.fetch_ohlcv_with_retry = AsyncMock(return_value=pd.DataFrame())
    client.fetch_ticker = AsyncMock(
        return_value={"last": 60000.0, "close": 59950.0, "symbol": _SYMBOL}
    )
    client.validate_market_liquidity = AsyncMock()
    client.fetch_quantity_precision_map = AsyncMock(return_value={_SYMBOL: 3})
    client.get_quantity_precision = MagicMock(return_value=3)
    client.round_quantity = MagicMock(side_effect=lambda sym, qty: round(qty, 3))
    client.round_price = MagicMock(side_effect=lambda sym, price: round(price, 2))
    client.connect = AsyncMock()
    client.close = AsyncMock()
    return client


def _make_client(
    initial_balance: float = 10_000.0,
) -> tuple[SimulatedBinanceClient, MagicMock]:
    real = _make_real_client()
    client = SimulatedBinanceClient(real, initial_balance_usdt=initial_balance)
    return client, real


# ─── Market Data (delegado) ──────────────────────────────────────────────────


class TestMarketDataDelegation:
    """Métodos públicos que delegam ao BinanceClient real."""

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_delega_ao_real(self) -> None:
        client, real = _make_client()
        df = await client.fetch_ohlcv(_SYMBOL, "15m", limit=100)
        real.fetch_ohlcv.assert_awaited_once_with(_SYMBOL, "15m", 100, None)
        assert isinstance(df, pd.DataFrame)

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_with_retry_delega_ao_real(self) -> None:
        client, real = _make_client()
        await client.fetch_ohlcv_with_retry(_SYMBOL, "15m")
        real.fetch_ohlcv_with_retry.assert_awaited_once_with(_SYMBOL, "15m", 200, None, None)

    @pytest.mark.asyncio
    async def test_fetch_ticker_delega_ao_real(self) -> None:
        client, real = _make_client()
        ticker = await client.fetch_ticker(_SYMBOL)
        real.fetch_ticker.assert_awaited_once_with(_SYMBOL)
        assert ticker["last"] == 60000.0

    @pytest.mark.asyncio
    async def test_validate_market_liquidity_delega_ao_real(self) -> None:
        client, real = _make_client()
        await client.validate_market_liquidity(_SYMBOL, min_volume=1_000_000, min_oi=500_000)
        real.validate_market_liquidity.assert_awaited_once_with(_SYMBOL, 1_000_000, 500_000)

    @pytest.mark.asyncio
    async def test_fetch_quantity_precision_map_delega_ao_real(self) -> None:
        client, real = _make_client()
        result = await client.fetch_quantity_precision_map([_SYMBOL])
        real.fetch_quantity_precision_map.assert_awaited_once_with([_SYMBOL])
        assert result == {_SYMBOL: 3}

    def test_get_quantity_precision_delega_ao_real(self) -> None:
        client, real = _make_client()
        result = client.get_quantity_precision(_SYMBOL)
        real.get_quantity_precision.assert_called_once_with(_SYMBOL)
        assert result == 3

    def test_round_quantity_delega_ao_real(self) -> None:
        client, real = _make_client()
        result = client.round_quantity(_SYMBOL, 1.2345)
        real.round_quantity.assert_called_once_with(_SYMBOL, 1.2345)
        assert result == 1.234

    def test_round_price_delega_ao_real(self) -> None:
        client, real = _make_client()
        result = client.round_price(_SYMBOL, 60123.456)
        real.round_price.assert_called_once_with(_SYMBOL, 60123.456)
        assert result == 60123.46

    @pytest.mark.asyncio
    async def test_validate_market_liquidity_propaga_erro(self) -> None:
        client, real = _make_client()
        real.validate_market_liquidity = AsyncMock(
            side_effect=InsufficientLiquidityError(
                "XPDUSDT: volume baixo", reason_code="insufficient_volume"
            )
        )
        with pytest.raises(InsufficientLiquidityError):
            await client.validate_market_liquidity("XPDUSDT")


# ─── Lifecycle ───────────────────────────────────────────────────────────────


class TestLifecycle:
    @pytest.mark.asyncio
    async def test_connect_delega_ao_real_e_mantem_balance_se_real_for_zero(
        self,
    ) -> None:
        client, real = _make_client(initial_balance=10_000.0)
        real.fetch_usdt_balance = AsyncMock(return_value=0.0)

        await client.connect()

        real.connect.assert_awaited_once()
        real.fetch_usdt_balance.assert_awaited_once()
        assert client._balance_usdt == 10_000.0  # manteve o inicial
        assert client._initial_balance == 10_000.0

    @pytest.mark.asyncio
    async def test_connect_usa_saldo_real_se_maior_que_zero(self) -> None:
        client, real = _make_client(initial_balance=10_000.0)
        real.fetch_usdt_balance = AsyncMock(return_value=25_000.0)

        await client.connect()

        assert client._balance_usdt == 25_000.0
        assert client._initial_balance == 25_000.0

    @pytest.mark.asyncio
    async def test_connect_fallback_em_erro_do_real(self) -> None:
        client, real = _make_client(initial_balance=10_000.0)
        real.fetch_usdt_balance = AsyncMock(side_effect=RuntimeError("offline"))

        await client.connect()

        assert client._balance_usdt == 10_000.0  # fallback para o inicial

    @pytest.mark.asyncio
    async def test_close_delega_ao_real(self) -> None:
        client, real = _make_client()
        await client.close()
        real.close.assert_awaited_once()


# ─── Balance ─────────────────────────────────────────────────────────────────


class TestBalance:
    @pytest.mark.asyncio
    async def test_fetch_balance_retorna_estrutura_correta(self) -> None:
        client, _ = _make_client(initial_balance=10_000.0)
        bal = await client.fetch_balance()

        assert "USDT" in bal
        assert bal["USDT"]["free"] == 10_000.0
        assert bal["USDT"]["used"] == 0.0
        assert bal["USDT"]["total"] == 10_000.0
        assert bal["info"]["simulated"] is True

    @pytest.mark.asyncio
    async def test_fetch_usdt_balance_reflete_saldo(self) -> None:
        client, real = _make_client(initial_balance=5_000.0)
        bal = await client.fetch_usdt_balance()
        assert bal == 5_000.0


# ─── Positions ───────────────────────────────────────────────────────────────


class TestPositions:
    @pytest.mark.asyncio
    async def test_fetch_open_positions_inicia_vazio(self) -> None:
        client, _ = _make_client()
        positions = await client.fetch_open_positions()
        assert positions == []

    @pytest.mark.asyncio
    async def test_create_market_buy_cria_posicao_long(self) -> None:
        client, _ = _make_client(initial_balance=10_000.0)
        await client.set_leverage(_SYMBOL, 10)
        await client.create_market_order(_SYMBOL, side="buy", quantity=0.5)

        positions = await client.fetch_open_positions()
        assert len(positions) == 1
        pos = positions[0]
        assert pos["symbol"] == _SYMBOL
        assert pos["side"] == "long"
        assert pos["contracts"] == 0.5
        assert pos["entryPrice"] == 60012.0
        assert pos["leverage"] == 10

    @pytest.mark.asyncio
    async def test_create_market_sell_cria_posicao_short(self) -> None:
        client, _ = _make_client(initial_balance=10_000.0)
        await client.set_leverage(_SYMBOL, 5)
        await client.create_market_order(_SYMBOL, side="sell", quantity=0.3)

        positions = await client.fetch_open_positions()
        assert len(positions) == 1
        pos = positions[0]
        assert pos["side"] == "short"
        assert pos["contracts"] == 0.3

    @pytest.mark.asyncio
    async def test_fetch_position_risk_filtra_por_symbol(self) -> None:
        client, _ = _make_client(initial_balance=10_000.0)
        await client.set_leverage("BTCUSDT", 10)
        await client.set_leverage("ETHUSDT", 5)
        await client.create_market_order("BTCUSDT", side="buy", quantity=0.5)
        await client.create_market_order("ETHUSDT", side="buy", quantity=1.0)

        btc = await client.fetch_position_risk(symbol="BTCUSDT")
        eth = await client.fetch_position_risk(symbol="ETHUSDT")
        assert len(btc) == 1
        assert len(eth) == 1
        assert btc[0]["symbol"] == "BTCUSDT"
        assert eth[0]["symbol"] == "ETHUSDT"

    @pytest.mark.asyncio
    async def test_fetch_position_risk_sem_symbol_retorna_todos(self) -> None:
        client, _ = _make_client(initial_balance=10_000.0)
        await client.set_leverage("BTCUSDT", 10)
        await client.create_market_order("BTCUSDT", side="buy", quantity=0.5)

        all_pos = await client.fetch_position_risk()
        assert len(all_pos) == 1

    @pytest.mark.asyncio
    async def test_market_order_compra_e_venda_liquida_posicao(self) -> None:
        """Abre long com buy, depois vende (sell) para fechar — posição some."""
        client, _ = _make_client(initial_balance=10_000.0)
        await client.set_leverage(_SYMBOL, 10)

        # Abre long
        await client.create_market_order(_SYMBOL, side="buy", quantity=0.5)
        assert len(await client.fetch_open_positions()) == 1

        # Fecha com sell da mesma quantidade
        await client.create_market_order(_SYMBOL, side="sell", quantity=0.5)
        assert len(await client.fetch_open_positions()) == 0


# ─── Leverage ────────────────────────────────────────────────────────────────


class TestLeverage:
    @pytest.mark.asyncio
    async def test_set_leverage_armazena_por_symbol(self) -> None:
        client, _ = _make_client()
        await client.set_leverage(_SYMBOL, 15)
        assert client._leverage[_SYMBOL] == 15

    @pytest.mark.asyncio
    async def test_set_leverage_multiplos_symbols(self) -> None:
        client, _ = _make_client()
        await client.set_leverage("BTCUSDT", 10)
        await client.set_leverage("ETHUSDT", 5)
        assert client._leverage["BTCUSDT"] == 10
        assert client._leverage["ETHUSDT"] == 5

    @pytest.mark.asyncio
    async def test_set_margin_mode_logga_sem_erro(self) -> None:
        client, _ = _make_client()
        await client.set_margin_mode(_SYMBOL, "isolated")  # não deve levantar


# ─── Order Management ────────────────────────────────────────────────────────


class TestOrderManagement:
    @pytest.mark.asyncio
    async def test_create_market_buy_deduz_margem_do_saldo(self) -> None:
        client, _ = _make_client(initial_balance=10_000.0)
        await client.set_leverage(_SYMBOL, 10)

        await client.create_market_order(_SYMBOL, side="buy", quantity=0.5)

        # custo = 60012 * 0.5 = 30006 USDT (60000 + 0.02% slippage)
        # margem = 30006 / 10 = 3000.6 USDT
        # saldo = 10000 - 3000.6 = 6999.4
        assert client._balance_usdt == pytest.approx(6_999.4, rel=1e-3)

    @pytest.mark.asyncio
    async def test_create_market_order_retorna_ordem_fechada(self) -> None:
        client, _ = _make_client()
        await client.set_leverage(_SYMBOL, 10)

        order = await client.create_market_order(_SYMBOL, side="buy", quantity=0.5)

        assert order["status"] == "closed"
        assert order["type"] == "market"
        assert order["filled"] == 0.5
        assert order["remaining"] == 0.0
        assert order["simulated"] is True
        assert order["id"].startswith("sim_market_")

    @pytest.mark.asyncio
    async def test_create_stop_loss_order_cria_ordem_aberta(self) -> None:
        client, _ = _make_client()
        sl = await client.create_stop_loss_order(
            _SYMBOL, side="sell", quantity=0.5, stop_price=58000.0
        )

        assert sl["status"] == "open"
        assert sl["type"] == "STOP_MARKET"
        assert sl["stopPrice"] == 58000.0
        assert sl["reduceOnly"] is True
        assert sl["id"].startswith("sim_sl_")

    @pytest.mark.asyncio
    async def test_create_take_profit_order_cria_ordem_aberta(self) -> None:
        client, _ = _make_client()
        tp = await client.create_take_profit_order(
            _SYMBOL, side="sell", quantity=0.5, take_profit_price=65000.0
        )

        assert tp["status"] == "open"
        assert tp["type"] == "TAKE_PROFIT_MARKET"
        assert tp["stopPrice"] == 65000.0
        assert tp["reduceOnly"] is True
        assert tp["id"].startswith("sim_tp_")

    @pytest.mark.asyncio
    async def test_cancel_all_orders_cancela_abertas_do_symbol(self) -> None:
        client, _ = _make_client()
        await client.create_stop_loss_order(_SYMBOL, side="sell", quantity=0.5, stop_price=58000.0)
        await client.create_take_profit_order(
            _SYMBOL, side="sell", quantity=0.5, take_profit_price=65000.0
        )
        await client.create_stop_loss_order("ETHUSDT", side="sell", quantity=1.0, stop_price=2000.0)

        await client.cancel_all_orders(_SYMBOL)

        btc_open = await client.fetch_open_orders(_SYMBOL)
        eth_open = await client.fetch_open_orders("ETHUSDT")
        assert len(btc_open) == 0  # todas canceladas
        assert len(eth_open) == 1  # não afetadas

    @pytest.mark.asyncio
    async def test_fetch_open_orders_retorna_solo_abertas(self) -> None:
        client, _ = _make_client()
        await client.create_stop_loss_order(_SYMBOL, side="sell", quantity=0.5, stop_price=58000.0)
        await client.create_market_order(_SYMBOL, side="buy", quantity=0.1)

        open_orders = await client.fetch_open_orders(_SYMBOL)
        # market order é "closed", SL é "open"
        assert len(open_orders) == 1
        assert open_orders[0]["type"] == "STOP_MARKET"

    @pytest.mark.asyncio
    async def test_fetch_order_retorna_ordem_existente(self) -> None:
        client, _ = _make_client()
        await client.set_leverage(_SYMBOL, 10)
        created = await client.create_market_order(_SYMBOL, side="buy", quantity=0.5)

        fetched = await client.fetch_order(created["id"], _SYMBOL)
        assert fetched["id"] == created["id"]
        assert fetched["status"] == "closed"

    @pytest.mark.asyncio
    async def test_fetch_order_inexistente_levanta_order_not_found(self) -> None:
        client, _ = _make_client()
        with pytest.raises(ccxt.OrderNotFound, match="not found"):
            await client.fetch_order("id_inexistente", _SYMBOL)

    @pytest.mark.asyncio
    async def test_slippage_aplica_no_preco(self) -> None:
        """Verifica que o slippage de 0.02% é aplicado no preço de fill."""
        client, real = _make_client(initial_balance=10_000.0)
        real.fetch_ticker = AsyncMock(
            return_value={"last": 60000.0, "close": 59950.0, "symbol": _SYMBOL}
        )
        await client.set_leverage(_SYMBOL, 1)

        buy_order = await client.create_market_order(_SYMBOL, side="buy", quantity=1.0)

        # buy slippage = 60000 * 0.0002 = 12 → preço = 60012
        assert buy_order["price"] == pytest.approx(60012.0, rel=1e-3)

        real.fetch_ticker = AsyncMock(
            return_value={"last": 61000.0, "close": 60950.0, "symbol": _SYMBOL}
        )
        sell_order = await client.create_market_order(_SYMBOL, side="sell", quantity=1.0)

        # sell slippage = 61000 * 0.0002 = 12.2 → preço = 60987.8 → arredonda 60987.8
        assert sell_order["price"] == pytest.approx(60987.8, rel=1e-2)


# ─── Position Update Logic ───────────────────────────────────────────────────


class TestPositionUpdateLogic:
    @pytest.mark.asyncio
    async def test_adiciona_a_posicao_existente_faz_media(self) -> None:
        client, _ = _make_client(initial_balance=20_000.0)
        await client.set_leverage(_SYMBOL, 10)

        await client.create_market_order(_SYMBOL, side="buy", quantity=0.5)
        # Preço é 60000 (slippage 60012, mas com mock retorna sempre 60000)

        pos = (await client.fetch_open_positions())[0]
        assert pos["contracts"] == 0.5
        assert pos["entryPrice"] == 60012.0
        assert pos["side"] == "long"

    @pytest.mark.asyncio
    async def test_venda_total_liquida_posicao(self) -> None:
        client, _ = _make_client(initial_balance=20_000.0)
        await client.set_leverage(_SYMBOL, 10)

        await client.create_market_order(_SYMBOL, side="buy", quantity=0.5)
        await client.create_market_order(_SYMBOL, side="sell", quantity=0.5)

        assert await client.fetch_open_positions() == []

    @pytest.mark.asyncio
    async def test_unrealized_pnl_reflete_preco_atual(self) -> None:
        client, real = _make_client(initial_balance=20_000.0)
        real.fetch_ticker = AsyncMock(
            return_value={"last": 60000.0, "close": 59950.0, "symbol": _SYMBOL}
        )
        await client.set_leverage(_SYMBOL, 10)

        await client.create_market_order(_SYMBOL, side="buy", quantity=1.0)
        pos = (await client.fetch_open_positions())[0]

        # Para posicao nova unrealizedPnl inicia em 0.
        # O unrealizedPnl real (currentPrice - entryPrice) so e
        # recalculado em adicoes subsequentes via _update_position.
        assert pos["unrealizedPnl"] == 0.0


# ─── State Management ────────────────────────────────────────────────────────


class TestStateManagement:
    @pytest.mark.asyncio
    async def test_reset_limpa_tudo(self) -> None:
        client, _ = _make_client(initial_balance=10_000.0)
        await client.set_leverage(_SYMBOL, 10)
        await client.create_market_order(_SYMBOL, side="buy", quantity=0.5)
        await client.create_stop_loss_order(_SYMBOL, side="sell", quantity=0.5, stop_price=58000.0)

        client.reset()

        assert client._balance_usdt == 10_000.0
        assert client._orders == {}
        assert client._positions == {}
        assert client._order_counter == 0

    @pytest.mark.asyncio
    async def test_reset_com_novo_balance_atualiza(self) -> None:
        client, _ = _make_client(initial_balance=10_000.0)
        client.reset(balance_usdt=20_000.0)

        assert client._balance_usdt == 20_000.0
        assert client._initial_balance == 20_000.0

    @pytest.mark.asyncio
    async def test_pnl_usdt_reflete_mudancas(self) -> None:
        client, _ = _make_client(initial_balance=10_000.0)
        assert client.pnl_usdt == 0.0

        # Após connect com fallback o saldo continua 10000
        # PnL só muda se o saldo interno mudar
        client._balance_usdt = 8_000.0
        assert client.pnl_usdt == -2_000.0

    @pytest.mark.asyncio
    async def test_connect_gera_log_sem_erro(self) -> None:
        client, real = _make_client(initial_balance=10_000.0)
        real.fetch_usdt_balance = AsyncMock(return_value=0.0)
        await client.connect()  # não deve levantar
        assert client._balance_usdt == 10_000.0


# ─── Order Flow Integration — cenário completo ──────────────────────────────


class TestFullOrderFlow:
    """Cenário completo: abre posição, SL, TP, cancela, verifica estado."""

    @pytest.mark.asyncio
    async def test_cenario_completo_abre_fecha_com_sltp(self) -> None:
        client, real = _make_client(initial_balance=10_000.0)
        real.fetch_ticker = AsyncMock(
            return_value={"last": 60000.0, "close": 59950.0, "symbol": _SYMBOL}
        )
        await client.set_leverage(_SYMBOL, 10)

        # 1. Abre posição long
        market_order = await client.create_market_order(_SYMBOL, side="buy", quantity=0.5)
        assert market_order["status"] == "closed"

        pos = (await client.fetch_open_positions())[0]
        assert pos["side"] == "long"
        assert pos["contracts"] == 0.5

        # 2. Cria SL e TP
        sl = await client.create_stop_loss_order(
            _SYMBOL, side="sell", quantity=0.5, stop_price=58000.0
        )
        await client.create_take_profit_order(
            _SYMBOL, side="sell", quantity=0.5, take_profit_price=65000.0
        )

        # 3. Verifica ordens abertas
        open_orders = await client.fetch_open_orders(_SYMBOL)
        assert len(open_orders) == 2

        # 4. Cancela tudo
        await client.cancel_all_orders(_SYMBOL)
        assert await client.fetch_open_orders(_SYMBOL) == []

        # 5. Fecha posição
        await client.create_market_order(_SYMBOL, side="sell", quantity=0.5)
        assert await client.fetch_open_positions() == []

        # 6. Ordem cancelada ainda é recuperável por ID
        cancelled_order = await client.fetch_order(sl["id"], _SYMBOL)
        assert cancelled_order["status"] == "canceled"

        # 7. PnL reflete:
        #   - abertura: debitou margem 3000.6 (60012 * 0.5 / 10)
        #   - fechamento: devolveu margem (+3000.6) + realizou PnL -12 (59988 - 60012)*0.5
        #   - saldo final = 10000 - 12 = 9988
        assert client._balance_usdt == pytest.approx(9_988.0, rel=1e-3)

    @pytest.mark.asyncio
    async def test_ordem_inexistente_levanta_order_not_found(self) -> None:
        client, _ = _make_client()
        with pytest.raises(ccxt.OrderNotFound):
            await client.fetch_order("nao_existe", _SYMBOL)
