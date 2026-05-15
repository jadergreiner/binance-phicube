"""
Entry point — Binance Phicube Auto Trade System.

Loop principal:
    Para cada (símbolo, timeframe) configurado, executa um monitor independente
    que acorda a cada candle fechada, avalia sinais e abre operações quando válido.

Controles de segurança:
    - Não abre nova posição se já existe uma aberta no mesmo símbolo
    - Respeita o limite global de posições abertas (max_open_positions)
    - Ignora a última candle (possivelmente incompleta) na avaliação de sinais
"""

from __future__ import annotations

import asyncio
import signal
import sys
import time
from datetime import UTC, datetime
from typing import Any

from src.common.loops import safe_loop
from src.common.serialization import SerializationFacade
from src.config.settings import ExitStrategy, SymbolConfig, get_settings  # noqa: F401
from src.exchange.base_client import TradingClient
from src.exchange.binance_client import BinanceClient, InsufficientLiquidityError
from src.exchange.resilient_binance_client import ResilientBinanceClient
from src.exchange.simulated_client import SimulatedBinanceClient
from src.monitoring import metrics
from src.monitoring.logger import configure_logging, get_logger
from src.monitoring.metrics import (
    observe_tick_duration,
    record_signal_rejected,
    update_heartbeat,
    update_positions_open,
)
from src.monitoring.order_monitor import OrderMonitor
from src.notifications import Notifier, NullNotifier, TelegramNotifier
from src.notifications.events import NotificationEvent, TradeOpenedEvent
from src.notifications.performance_reporter import PerformanceReporter
from src.resilience.exceptions import CircuitBreakerOpenError
from src.storage.repository import MongoRepository
from src.storage.resilient_repository import ResilientMongoRepository
from src.strategy.plugin_base import SignalResult
from src.strategy.plugin_registry import PluginRegistry
from src.strategy.signal_engine import Direction, Signal, SignalEngine
from src.trading.order_manager import OrderManager, TradeStatus
from src.trading.risk_manager import RiskManager, RiskRejection
from src.trading.trade_close_router import TradeCloseRouter
from tools.backup_mongo import check_last_backup

logger = get_logger(__name__)

# Horário do backup diário (UTC)
_BACKUP_HOUR_UTC = 3
_BACKUP_MINUTE_UTC = 0

# Seconds to wait between each candle-close poll per (symbol, timeframe)
_TIMEFRAME_SECONDS: dict[str, int] = {
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "2h": 7200,
    "4h": 14400,
    "6h": 21600,
    "8h": 28800,
    "12h": 43200,
    "1d": 86400,
}


class HeartbeatTask:
    """Grava sinal periódico de vida do processo na collection audit (SPEC_017).

    Também reprocessa trades journaled a cada intervalo (eventual consistency).
    """

    INTERVAL_SECONDS: int = 300
    # Reprocessa journal a cada N ciclos (300s * 3 = 900s = 15 min)
    JOURNAL_REPROCESS_INTERVAL_CYCLES: int = 3

    def __init__(
        self,
        repo: MongoRepository | ResilientMongoRepository,
        monitor_count: int,
        monitor_count_getter: callable | None = None,
    ) -> None:
        self._repo = repo
        self._monitor_count = monitor_count
        self._monitor_count_getter = monitor_count_getter
        self._started_at = datetime.now(UTC)
        self._cycle_count = 0

    async def _beat(self) -> None:
        """Grava heartbeat na collection audit e reprocessa journal periodicamente."""
        uptime_seconds = int((datetime.now(UTC) - self._started_at).total_seconds())
        monitor_count = (
            self._monitor_count_getter() if self._monitor_count_getter else self._monitor_count
        )
        await self._repo.audit(
            "heartbeat",
            {
                "process_uptime_seconds": uptime_seconds,
                "monitor_count": monitor_count,
                "metadata": {"source": "HeartbeatTask"},
            },
        )

        # Reprocessar journal a cada N ciclos (eventual consistency)
        self._cycle_count += 1
        if self._cycle_count % self.JOURNAL_REPROCESS_INTERVAL_CYCLES == 0:
            await self._reprocess_journal()

    async def _reprocess_journal(self) -> None:
        """Tenta reprocessar trades journaled do ResilientMongoRepository."""
        # Verifica se repo tem journal (ResilientMongoRepository)
        if not isinstance(self._repo, ResilientMongoRepository):
            return

        try:
            # Pega o journal do repositório resiliente
            journal = self._repo._journal
            reprocessed, failed = await journal.reprocess_pending_trades(self._repo)

            if reprocessed > 0 or failed > 0:
                logger.info(
                    "journal_reprocess_cycle",
                    reprocessed=reprocessed,
                    failed=failed,
                    cycle=self._cycle_count,
                )
        except Exception as exc:
            logger.warning(
                "journal_reprocess_failed",
                error_type=type(exc).__name__,
                cycle=self._cycle_count,
            )

    async def run(self) -> None:
        def _log_heartbeat_error(exc: BaseException) -> None:
            logger.debug("heartbeat_failed", error_type=type(exc).__name__)

        await safe_loop(
            self._beat,
            interval=self.INTERVAL_SECONDS,
            logger=logger,
            loop_name="heartbeat",
            on_error=_log_heartbeat_error,
        )


class BackupTask:
    """Executa backup MongoDB diário às 03:00 UTC (SPEC_031).

    Padrão: mesma estrutura de HeartbeatTask.
    Usa asyncio.sleep dinâmico para acordar na hora agendada.
    """

    def __init__(
        self,
        mongodb_uri: str,
        backup_dir: str = "./backups/mongo",
        notifier: Notifier | None = None,
    ) -> None:
        self._mongodb_uri = mongodb_uri
        self._backup_dir = backup_dir
        self._notifier = notifier

    async def run(self) -> None:
        while True:
            try:
                await self._run_once()
            except asyncio.CancelledError:
                return
            except Exception as exc:
                logger.error("backup_task_failed", error_type=type(exc).__name__)

            # Aguardar até o próximo dia às 03:00 UTC
            await self._sleep_until_next()

    async def _run_once(self) -> None:
        from tools.backup_mongo import MongoBackup  # noqa: PLC0415

        logger.info("backup_task_starting")
        backup = MongoBackup(
            mongodb_uri=self._mongodb_uri,
            backup_dir=self._backup_dir,
            notifier=self._notifier,
        )
        record = await backup.run(verify=True)
        if record is not None:
            logger.info(
                "backup_task_completed",
                file=record.file_path,
                size_bytes=record.file_size_bytes,
                duration_s=record.duration_seconds,
            )

    async def _sleep_until_next(self) -> None:
        """Calcula segundos até a próxima 03:00 UTC e dorme."""
        now = datetime.now(UTC)
        next_run = now.replace(
            hour=_BACKUP_HOUR_UTC,
            minute=_BACKUP_MINUTE_UTC,
            second=0,
            microsecond=0,
        )
        if next_run <= now:
            # Já passou das 03:00 hoje → agenda para amanhã
            next_run = next_run.replace(day=next_run.day + 1)

        delay = (next_run - now).total_seconds()
        logger.debug("backup_task_next_run", next_run=next_run.isoformat(), delay_s=int(delay))
        await asyncio.sleep(delay)


class RuntimeMonitorRegistry:
    """Gerencia ciclo de vida de TradingMonitors em runtime.

    Cada TradingMonitor recebe sua própria instância de SignalEngine
    (INV-033-06). PluginRegistry é inicializado no construtor e
    plugins são descobertos via entry_points na inicialização.
    """

    def __init__(
        self,
        *,
        settings: Any,
        client: TradingClient,
        repo: MongoRepository | ResilientMongoRepository,
        resilient_client: ResilientBinanceClient | None = None,
        resilient_repo: ResilientMongoRepository | None = None,
        notifier: Notifier,
        router: TradeCloseRouter,
    ) -> None:
        self._settings = settings
        self._client = client
        self._repo = repo
        # Facades com fallback para client/repo diretos (backward compatibility)
        self._resilient_client = resilient_client or client
        self._resilient_repo = resilient_repo or repo
        self._notifier = notifier
        self._router = router
        self._tasks: dict[tuple[str, str], asyncio.Task] = {}
        self._configs: dict[tuple[str, str], SymbolConfig] = {}
        self._plugin_registry = PluginRegistry(plugin_timeout=settings.plugin_timeout)

    @property
    def monitor_count(self) -> int:
        return len(self._tasks)

    def _build_monitor(self, cfg: SymbolConfig, router: TradeCloseRouter) -> TradingMonitor:
        risk_manager = RiskManager(
            risk_per_trade_pct=self._settings.risk_per_trade_pct,
            leverage=cfg.leverage,
            max_capital_allocation_pct=self._settings.max_capital_allocation_pct,
            sizing_mode=self._settings.sizing_mode,
            risk_per_trade_usdt=self._settings.risk_per_trade_usdt,
            atr_period=self._settings.atr_period,
            atr_multiplier=self._settings.atr_multiplier,
            min_position_usdt=self._settings.min_position_usdt,
            max_position_usdt=self._settings.max_position_usdt,
            get_atr_multiplier_override=self._settings.atr_multiplier_overrides.get,
            max_position_pct=self._settings.max_position_pct,
            slippage_validation_enabled=self._settings.slippage_validation_enabled,
            slippage_tolerance_multiplier=self._settings.slippage_tolerance_multiplier,
            slippage_tolerance_reduced=self._settings.slippage_tolerance_reduced,
            liq_map=self._settings.backtest_slippage_liq_map,
            slippage_map=self._settings.backtest_slippage_by_liq,
            predictive_breaker_enabled=self._settings.predictive_breaker_enabled,
            predictive_breaker_percentile=self._settings.predictive_breaker_percentile,
            predictive_breaker_window=self._settings.predictive_breaker_window,
            predictive_breaker_tiers=self._settings.predictive_breaker_tiers,
            get_portfolio_reduction=lambda: (
                router.portfolio_risk_reduction_factor if router.portfolio_breaker_active else 1.0
            ),
        )
        router.register(cfg.symbol, risk_manager)
        order_manager = OrderManager(
            self._client,
            leverage=cfg.leverage,
            notifier=self._notifier,
            exit_strategy=self._settings.exit_strategy,
            tp_levels=self._settings.tp_levels,
            trailing_activation_pct=self._settings.trailing_activation_pct,
            trailing_callback_rate=self._settings.trailing_callback_rate,
        )
        # Cada monitor com sua própria instância de SignalEngine (INV-033-06)
        monitor_signal_engine = self._make_signal_engine()
        return TradingMonitor(
            config=cfg,
            client=self._client,
            repo=self._repo,
            resilient_client=self._resilient_client,
            resilient_repo=self._resilient_repo,
            signal_engine=monitor_signal_engine,
            risk_manager=risk_manager,
            order_manager=order_manager,
            notifier=self._notifier,
            max_open_positions=self._settings.max_open_positions,
            warmup_candles=self._settings.warmup_candles,
            tick_pipeline_enabled=getattr(self._settings, "tick_pipeline_enabled", False),
        )

    def _init_plugin_registry(self) -> None:
        """Inicializa o PluginRegistry: discovery via entry_points + fallback.

        Se discovery falhar, registra WilliamsStrategy manualmente
        como fallback (Regra Mestre — INV-033-03).
        """
        try:
            self._plugin_registry.discover_and_register_all()
            logger.info("plugin_registry_initialized_via_discovery")
        except RuntimeError:
            logger.warning("no_plugins_discovered_via_entry_points_registering_williams_fallback")
            from src.strategies.williams_strategy import WilliamsStrategy

            self._plugin_registry.register("williams", WilliamsStrategy())
            logger.info("plugin_williams_registered_as_fallback")

        self._plugin_registry.validate_master()

    def _make_signal_engine(self) -> SignalEngine:
        return SignalEngine(
            plugin_registry=self._plugin_registry,
            default_strategy=self._settings.default_strategy,
            risk_reward_ratio=self._settings.risk_reward_ratio,
            symbol_strategy_map=self._settings.symbol_strategy_map,
        )

    async def add(self, cfg: SymbolConfig) -> None:
        key = (cfg.symbol, cfg.timeframe)
        if key in self._tasks:
            if self._configs[key].leverage != cfg.leverage:
                await self.remove(*key)
            else:
                return

        try:
            await self._client.validate_market_liquidity(cfg.symbol)
        except InsufficientLiquidityError as exc:
            logger.warning(
                "runtime_monitor_skipped_insufficient_liquidity",
                symbol=cfg.symbol,
                timeframe=cfg.timeframe,
                leverage=cfg.leverage,
                reason_code=exc.reason_code,
                error_type=type(exc).__name__,
            )
            return

        await self._client.set_leverage(cfg.symbol, cfg.leverage)
        monitor = self._build_monitor(cfg, self._router)
        task = asyncio.create_task(monitor.run())
        self._tasks[key] = task
        self._configs[key] = cfg
        logger.info(
            "runtime_monitor_added",
            symbol=cfg.symbol,
            timeframe=cfg.timeframe,
            leverage=cfg.leverage,
        )

    async def remove(self, symbol: str, timeframe: str) -> None:
        key = (symbol, timeframe)
        task = self._tasks.pop(key, None)
        self._configs.pop(key, None)
        if task is None:
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        logger.info("runtime_monitor_removed", symbol=symbol, timeframe=timeframe)

    async def reconcile(self, desired_configs: list[SymbolConfig]) -> None:
        desired: dict[tuple[str, str], SymbolConfig] = {
            (cfg.symbol, cfg.timeframe): cfg for cfg in desired_configs
        }
        running = set(self._tasks.keys())
        desired_keys = set(desired.keys())

        for symbol, timeframe in sorted(running - desired_keys):
            await self.remove(symbol, timeframe)

        for key in sorted(desired_keys):
            await self.add(desired[key])

    async def close(self) -> None:
        for symbol, timeframe in list(self._tasks.keys()):
            await self.remove(symbol, timeframe)

    def active_pairs(self) -> list[tuple[str, str, int]]:
        return [(cfg.symbol, cfg.timeframe, cfg.leverage) for cfg in self._configs.values()]


class RuntimeMonitorSyncTask:
    """Sincroniza monitores ativos com sessões APPROVED do onboarding."""

    def __init__(
        self,
        *,
        settings: Any,
        repo: MongoRepository,
        registry: RuntimeMonitorRegistry,
    ) -> None:
        self._settings = settings
        self._repo = repo
        self._registry = registry
        self._interval_seconds = int(settings.runtime_monitor_auto_sync_interval_seconds)

    @staticmethod
    def _base_configs(settings: Any) -> list[SymbolConfig]:
        return [
            SymbolConfig(symbol=cfg.symbol, timeframe=cfg.timeframe, leverage=cfg.leverage)
            for cfg in settings.symbol_timeframes
        ]

    @staticmethod
    def _approved_configs(sessions: list[dict[str, Any]]) -> list[SymbolConfig]:
        approved: dict[tuple[str, str], SymbolConfig] = {}
        for session in sessions:
            if session.get("status") != "APPROVED":
                continue
            symbol = str(session.get("symbol", "")).upper().strip()
            timeframe = str(session.get("timeframe", "")).strip()
            leverage_raw = session.get("leverage")
            if not symbol or not timeframe:
                continue
            try:
                leverage = int(leverage_raw)
            except (TypeError, ValueError):
                continue
            if leverage <= 0:
                continue
            approved[(symbol, timeframe)] = SymbolConfig(
                symbol=symbol,
                timeframe=timeframe,
                leverage=leverage,
            )
        return list(approved.values())

    async def _desired_configs(self) -> list[SymbolConfig]:
        sessions = await self._repo.list_onboarding_sessions()
        base: dict[tuple[str, str], SymbolConfig] = {
            (cfg.symbol, cfg.timeframe): cfg for cfg in self._base_configs(self._settings)
        }
        for cfg in self._approved_configs(sessions):
            base[(cfg.symbol, cfg.timeframe)] = cfg
        return list(base.values())

    async def sync_once(self) -> None:
        desired = await self._desired_configs()
        await self._registry.reconcile(desired)
        logger.info(
            "runtime_monitor_sync_completed",
            desired_count=len(desired),
            active_count=self._registry.monitor_count,
            active_pairs=self._registry.active_pairs(),
        )

    async def run(self) -> None:
        def _log_sync_error(exc: BaseException) -> None:
            logger.error("runtime_monitor_sync_failed", error_type=type(exc).__name__)

        await safe_loop(
            self.sync_once,
            interval=self._interval_seconds,
            logger=logger,
            loop_name="runtime_monitor_sync",
            on_error=_log_sync_error,
        )


async def _health_server(host: str = "0.0.0.0", port: int = 8081) -> None:
    """Servidor HTTP mínimo para Docker healthcheck. Responde 200 (SPEC_017)."""

    async def _handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            await reader.read(1024)
            writer.write(
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: application/json\r\n"
                b"Content-Length: 16\r\n"
                b"\r\n"
                b'{"status": "ok"}'
            )
            await writer.drain()
        finally:
            writer.close()

    try:
        server = await asyncio.start_server(_handle, host, port)
        logger.info("health_server_started", host=host, port=port)
        async with server:
            await server.serve_forever()
    except asyncio.CancelledError:
        return
    except Exception as exc:
        logger.error("health_server_failed", error_type=type(exc).__name__)


def _create_notifier(settings) -> Notifier:
    """Cria notificador baseado nas configurações do Telegram."""
    if settings.telegram_token and settings.telegram_chat_id:
        return TelegramNotifier(
            token=settings.telegram_token,
            chat_id=settings.telegram_chat_id,
        )
    return NullNotifier()


class TradingMonitor:
    """Monitors one SymbolConfig triplet and acts on closed candles.

    Usa Facades (ResilientBinanceClient e ResilientMongoRepository) via DI
    para tratamento de CircuitBreakerOpenError.
    """

    def __init__(
        self,
        config: SymbolConfig,
        client: Any,
        repo: MongoRepository | ResilientMongoRepository,
        signal_engine: SignalEngine,
        risk_manager: RiskManager,
        order_manager: OrderManager,
        notifier: Notifier,
        max_open_positions: int,
        warmup_candles: int,
        tick_pipeline_enabled: bool = False,
        resilient_client: ResilientBinanceClient | None = None,
        resilient_repo: ResilientMongoRepository | None = None,
    ) -> None:
        self._config = config
        self._symbol = config.symbol
        self._timeframe = config.timeframe
        self._client = client
        self._repo = repo
        # Facades com fallback para client/repo diretos (backward compatibility)
        self._resilient_client = resilient_client or client
        self._resilient_repo = resilient_repo or repo
        self._signal_engine = signal_engine
        self._risk_manager = risk_manager
        self._order_manager = order_manager
        self._notifier = notifier
        self._max_positions = max_open_positions
        self._warmup_candles = warmup_candles
        self._tick_pipeline_enabled = tick_pipeline_enabled
        # Intervalo derivado do timeframe — corrige bug de 300 s fixo (SPEC_018)
        self._interval = _TIMEFRAME_SECONDS.get(config.timeframe, 300)
        # SPEC_034: Inicializar pipeline se habilitado
        self._pipeline = None
        if self._tick_pipeline_enabled:
            self._init_pipeline()

    def _init_pipeline(self) -> None:
        from src.trading.middlewares import (
            CalculateRiskMiddleware,
            EvaluateSignalMiddleware,
            ExecuteTradeMiddleware,
            FetchCandlesMiddleware,
            NotifyMiddleware,
            ValidateLimitsMiddleware,
        )
        from src.trading.tick_pipeline import TickPipeline

        self._pipeline = (
            TickPipeline()
            .use(FetchCandlesMiddleware(self._client, self._warmup_candles))
            .use(ValidateLimitsMiddleware(self._repo, self._max_positions))
            .use(EvaluateSignalMiddleware(self._signal_engine))
            .use(CalculateRiskMiddleware(self._client, self._risk_manager, self._repo))
            .use(ExecuteTradeMiddleware(self._order_manager, self._repo))
            .use(NotifyMiddleware(self._notifier))
        )

    async def run(self) -> None:
        async def _on_start() -> None:
            logger.info("monitor_started", symbol=self._symbol, timeframe=self._timeframe)

        async def _on_stop() -> None:
            logger.info("monitor_stopped", symbol=self._symbol, timeframe=self._timeframe)

        def _log_tick_error(exc: BaseException) -> None:
            logger.error(
                "monitor_tick_error",
                symbol=self._symbol,
                timeframe=self._timeframe,
                error_type=type(exc).__name__,
                exc_info=True,
            )

        await safe_loop(
            self._tick,
            interval=self._interval,
            logger=logger,
            loop_name=f"{self._symbol}_{self._timeframe}",
            on_start=_on_start,
            on_stop=_on_stop,
            on_error=_log_tick_error,
        )

    async def _tick(self) -> None:
        # SPEC_034: Usar pipeline quando habilitado
        if self._tick_pipeline_enabled and self._pipeline is not None:
            await self._tick_pipeline()
            return

        # SPEC_032: Medir duração do tick
        tick_start = time.time()

        # SPEC_032: Atualizar heartbeat
        update_heartbeat()

        # Fetch closed candles — request one extra and drop the last (open) candle
        # TASK_034: Usar ResilientBinanceClient com tratamento de CircuitBreakerOpenError
        try:
            df = await self._resilient_client.fetch_ohlcv_with_retry(
                symbol=self._symbol,
                timeframe=self._timeframe,
                limit=self._warmup_candles + 1,
            )
        except CircuitBreakerOpenError:
            # CircuitBreaker OPEN em fetch_ohlcv: log WARNING, usar cache, continuar loop
            logger.warning(
                "fetch_ohlcv_circuit_breaker_open",
                symbol=self._symbol,
                timeframe=self._timeframe,
            )
            # Registrar duração do tick antes de retornar
            observe_tick_duration(
                self._symbol,
                self._timeframe,
                time.time() - tick_start,
            )
            return

        # Discard the last (potentially incomplete) candle
        df = df.iloc[:-1].reset_index(drop=True)

        # Check if we can open new positions
        total_open = await self._resilient_repo.count_open_trades()
        # SPEC_032: Atualizar métrica de posições abertas
        update_positions_open(total_open)

        if total_open >= self._max_positions:
            logger.debug(
                "max_positions_reached",
                open=total_open,
                max=self._max_positions,
            )
            # SPEC_032: Registrar duração do tick antes de retornar
            observe_tick_duration(
                self._symbol,
                self._timeframe,
                time.time() - tick_start,
            )
            return

        # Check if this symbol already has an open position
        symbol_trades = await self._repo.get_open_trades_for_symbol(self._symbol)
        if symbol_trades:
            logger.debug("symbol_already_in_trade", symbol=self._symbol)
            # SPEC_032: Registrar duração do tick antes de retornar
            observe_tick_duration(
                self._symbol,
                self._timeframe,
                time.time() - tick_start,
            )
            return

        # Evaluate signal
        signal_result = await self._signal_engine.evaluate(self._symbol, self._timeframe, df)
        await self._persist_signal_evaluation()
        if not signal_result:
            observe_tick_duration(
                self._symbol,
                self._timeframe,
                time.time() - tick_start,
            )
            return

        # SignalResult → Signal legado (compatibilidade retroativa)
        if not isinstance(signal_result, SignalResult):
            raise TypeError(
                f"Expected SignalResult after falsy check, got {type(signal_result).__name__}"
            )
        signal = Signal(
            symbol=self._symbol,
            timeframe=self._timeframe,
            direction=Direction(signal_result.direction),
            entry_price=signal_result.entry_price,
            stop_loss=signal_result.stop_loss,
            take_profit=signal_result.take_profit,
            fractal_ref=(signal_result.metadata or {}).get("fractal_ref", 0.0),
        )

        # Persist signal regardless of execution
        signal_id = await self._repo.save_signal(signal.to_dict())
        await self._repo.audit("signal_detected", signal.to_dict())

        # Calculate position size
        balance = await self._client.fetch_usdt_balance()
        if balance <= 0:
            await self._set_signal_outcome(
                signal_id,
                execution_status="REJECTED_NO_BALANCE",
                execution_reason="zero_or_negative_balance",
                execution_details={"balance": balance},
            )
            logger.warning("zero_balance", symbol=self._symbol)
            # SPEC_032: Registrar duração do tick antes de retornar
            observe_tick_duration(
                self._symbol,
                self._timeframe,
                time.time() - tick_start,
            )
            return

        qty_precision = self._client.get_quantity_precision(self._symbol)
        intraday_realized_pnl_usdt = await self._repo.get_intraday_realized_pnl_usdt()
        position_result = self._risk_manager.calculate(
            signal,
            balance,
            qty_precision,
            intraday_realized_pnl_usdt=intraday_realized_pnl_usdt,
            df=df,
        )
        if position_result.is_err():
            rejection = position_result.unwrap_err()
            # SPEC_032: Registrar sinal rejeitado pelo RiskManager
            if rejection:
                record_signal_rejected(self._symbol, rejection.code)
            (
                execution_status,
                execution_reason,
                execution_details,
            ) = self._map_risk_rejection_outcome(rejection)
            await self._set_signal_outcome(
                signal_id,
                execution_status=execution_status,
                execution_reason=execution_reason,
                execution_details=execution_details,
            )
            logger.warning("position_size_rejected", symbol=self._symbol)
            # SPEC_032: Registrar duração do tick antes de retornar
            observe_tick_duration(
                self._symbol,
                self._timeframe,
                time.time() - tick_start,
            )
            return

        position = position_result.unwrap()
        # Execute trade
        # TASK_034: Tratar CircuitBreakerOpenError em create_order
        try:
            trade_result = await self._order_manager.execute(signal, position)
        except CircuitBreakerOpenError as exc:
            # CircuitBreaker OPEN em create_order: log ERROR, Telegram alert, PARAR loop
            logger.error(
                "create_order_circuit_breaker_open",
                symbol=self._symbol,
                timeframe=self._timeframe,
                error_type=type(exc).__name__,
            )
            await self._set_signal_outcome(
                signal_id,
                execution_status="REJECTED_ORDER_EXECUTION",
                execution_reason="circuit_breaker_open_create_order",
            )
            # Enviar alert via Telegram
            await self._notifier.send(
                NotificationEvent.CRITICAL_ERROR,
                type(
                    "Alert",
                    (),
                    {
                        "to_message": lambda: (
                            f"🚨 **CircuitBreaker OPEN**\n"
                            f"Símbolo: {self._symbol}\n"
                            f"Operação: create_order\n"
                            f"Loop parado para {self._symbol}/{self._timeframe}"
                        )
                    },
                )(),
            )
            # Registrar duração do tick antes de parar o loop
            observe_tick_duration(
                self._symbol,
                self._timeframe,
                time.time() - tick_start,
            )
            raise  # Parar o loop

        if trade_result.is_err():
            await self._set_signal_outcome(
                signal_id,
                execution_status="REJECTED_ORDER_EXECUTION",
                execution_reason="order_manager_execute_returned_error",
            )
            logger.error("trade_execution_failed", symbol=self._symbol)
            # SPEC_032: Registrar duração do tick antes de retornar
            observe_tick_duration(
                self._symbol,
                self._timeframe,
                time.time() - tick_start,
            )
            return

        trade = trade_result.unwrap()
        # TASK_034: Usar ResilientMongoRepository com fallback a journal
        trade_id = await self._resilient_repo.save_trade(trade)
        await self._resilient_repo.audit(
            "trade_opened",
            {"trade_id": trade_id, **trade.to_dict()},
        )
        if trade.status == TradeStatus.OPEN:
            await self._set_signal_outcome(
                signal_id,
                execution_status="TRADE_OPENED",
                execution_reason="trade_opened",
                trade_id=trade_id,
            )
        else:
            await self._set_signal_outcome(
                signal_id,
                execution_status="REJECTED_ORDER_EXECUTION",
                execution_reason="trade_saved_with_failed_status",
                execution_details={"trade_status": trade.status.value},
                trade_id=trade_id,
            )

        if trade.status == TradeStatus.OPEN:
            # Send notification for successful trade
            await self._notifier.send(
                NotificationEvent.TRADE_OPENED,
                TradeOpenedEvent(
                    symbol=trade.symbol,
                    direction=trade.direction,
                    quantity=trade.quantity,
                    entry_price=trade.entry_price,
                    stop_loss=trade.stop_loss,
                    take_profit=trade.take_profit,
                    risk_amount=trade.risk_amount,
                    timestamp=trade.opened_at,
                ),
            )
        elif trade.status == TradeStatus.FAILED:
            logger.error("trade_saved_as_failed", symbol=self._symbol, trade_id=trade_id)

        # SPEC_032: Registrar duração do tick no final do método
        observe_tick_duration(
            self._symbol,
            self._timeframe,
            time.time() - tick_start,
        )

    async def _tick_pipeline(self) -> None:
        from src.trading.tick_pipeline import TickContext

        tick_start = time.time()
        update_heartbeat()

        context = TickContext(
            symbol=self._symbol,
            timeframe=self._timeframe,
        )

        if self._pipeline is None:
            logger.error("tick_pipeline_not_initialized", symbol=self._symbol)
            return
        result = await self._pipeline.execute(context)

        if result.aborted:
            logger.debug(
                "tick_pipeline_aborted",
                symbol=self._symbol,
                timeframe=self._timeframe,
                reason=result.abort_reason,
                metrics=result.metrics,
            )
        else:
            logger.debug(
                "tick_pipeline_completed",
                symbol=self._symbol,
                timeframe=self._timeframe,
                metrics=result.metrics,
            )

        observe_tick_duration(
            self._symbol,
            self._timeframe,
            time.time() - tick_start,
        )

    async def _persist_signal_evaluation(self) -> None:
        consume = getattr(self._signal_engine, "consume_last_evaluation", None)
        if not callable(consume):
            return

        evaluation = consume()
        if evaluation is None:
            return

        payload = SerializationFacade.to_payload(evaluation)
        if not isinstance(payload, dict):
            return

        await self._repo.audit("signal_evaluated", payload)

    async def _set_signal_outcome(
        self,
        signal_id: str,
        *,
        execution_status: str,
        execution_reason: str | None = None,
        execution_details: dict[str, Any] | None = None,
        trade_id: str | None = None,
    ) -> None:
        updated = await self._repo.update_signal_execution_outcome(
            signal_id,
            execution_status=execution_status,
            execution_reason=execution_reason,
            execution_details=execution_details,
            trade_id=trade_id,
        )
        if not updated:
            logger.warning(
                "signal_outcome_not_updated",
                signal_id=signal_id,
                execution_status=execution_status,
            )

    @staticmethod
    def _map_risk_rejection_outcome(
        rejection: RiskRejection | None,
    ) -> tuple[str, str | None, dict[str, Any] | None]:
        if rejection is None:
            return "REJECTED_UNKNOWN", "risk_rejected_without_structured_reason", None

        mapping: dict[str, str] = {
            "MAX_CAPITAL_ALLOCATION_EXCEEDED": "REJECTED_RISK_MAX_CAPITAL",
            "ZERO_STOP_DISTANCE": "REJECTED_RISK_ZERO_STOP",
            "QTY_ZERO_AFTER_ROUNDING": "REJECTED_RISK_QTY_ZERO",
            "MIN_NOTIONAL_NOT_MET": "REJECTED_RISK_MIN_NOTIONAL",
            "INTRADAY_LOSS_LIMIT_REACHED": "REJECTED_RISK_INTRADAY_LOSS_LIMIT",
            "SLIPPAGE_EXCEEDS_TOLERANCE": "REJECTED_RISK_SLIPPAGE",
            "CIRCUIT_BREAKER_ACTIVE": "REJECTED_RISK_CIRCUIT_BREAKER",
            "PREDICTIVE_CIRCUIT_BREAKER_SKIPPED": "REJECTED_RISK_PREDICTIVE_CIRCUIT_BREAKER",
        }
        execution_status = mapping.get(rejection.code, "REJECTED_UNKNOWN")
        details = rejection.details or None
        return execution_status, rejection.reason, details


async def _main() -> None:
    settings = get_settings()
    configure_logging(
        settings.log_level,
        log_file="logs/bot.log" if settings.simulation_mode else None,
    )

    # SPEC_032: Inicializar métricas Prometheus
    metrics.initialize(
        testnet=settings.binance_testnet,
    )
    if settings.prometheus_enabled:
        metrics.start_metrics_server(
            port=settings.prometheus_port,
            bind_host=settings.prometheus_bind_host,
        )

    configs = settings.symbol_timeframes

    logger.info(
        "phicube_starting",
        pairs=[(c.symbol, c.timeframe, c.leverage) for c in configs],
        testnet=settings.binance_testnet,
        risk_pct=settings.risk_per_trade_pct,
    )

    real_client = BinanceClient(settings)
    if settings.simulation_mode:
        client: BinanceClient | SimulatedBinanceClient = SimulatedBinanceClient(
            real_client,
            initial_balance_usdt=settings.simulation_initial_balance,
        )
    else:
        client = real_client
    await client.connect()

    repo = MongoRepository(
        settings.mongodb_uri,
        settings.mongodb_database,
        trade_history_retention_days=settings.trade_history_retention_days,
    )
    await repo.setup_indexes()

    notifier = _create_notifier(settings)

    # TASK_034: Criar Facades para resiliência com Circuit Breaker
    resilient_client = ResilientBinanceClient(
        real_client=client,
        settings=settings,
    )
    resilient_repo = ResilientMongoRepository(
        real_repo=repo,
        notifier=notifier,
    )

    # SPEC_043 — TradeCloseRouter criado ANTES de RuntimeMonitorRegistry
    trade_close_router = TradeCloseRouter(
        portfolio_loss_threshold=settings.portfolio_loss_threshold,
        portfolio_risk_reduction_factor=settings.portfolio_risk_reduction_factor,
    )

    # SPEC_033 — Cada TradingMonitor cria seu próprio SignalEngine
    # Nenhuma instância compartilhada (INV-033-06)
    # TASK_034: Passar Facades ao RuntimeMonitorRegistry via DI
    monitor_registry = RuntimeMonitorRegistry(
        settings=settings,
        client=client,
        repo=repo,
        resilient_client=resilient_client,
        resilient_repo=resilient_repo,
        notifier=notifier,
        router=trade_close_router,
    )
    monitor_registry._init_plugin_registry()

    reporter = PerformanceReporter(
        repository=repo,
        notifier=notifier,
        interval_hours=settings.performance_report_interval_hours,
    )

    order_monitor = OrderMonitor(
        client=client,
        repository=repo,
        notifier=notifier,
        renotify_interval_seconds=settings.sl_missing_renotify_interval_minutes * 60,
        manual_close_confirm_cycles=settings.order_monitor_manual_close_confirm_cycles,
        manual_close_require_dual_source=settings.order_monitor_manual_close_require_dual_source,
        on_trade_closed=trade_close_router,
    )

    # SPEC_031: Verificar status do último backup no startup
    await check_last_backup("./backups/mongo")

    tasks: list[asyncio.Task] = []
    runtime_sync_task: RuntimeMonitorSyncTask | None = None
    if settings.runtime_monitor_auto_sync:
        runtime_sync_task = RuntimeMonitorSyncTask(
            settings=settings,
            repo=repo,
            registry=monitor_registry,
        )
        await runtime_sync_task.sync_once()
        tasks.append(asyncio.create_task(runtime_sync_task.run()))
    else:
        await monitor_registry.reconcile(configs)

    tasks.append(asyncio.create_task(reporter.run()))
    tasks.append(asyncio.create_task(order_monitor.run()))
    # TASK_034: Passar ResilientMongoRepository ao HeartbeatTask para journal reprocessing
    tasks.append(
        asyncio.create_task(
            HeartbeatTask(
                repo=resilient_repo,
                monitor_count=monitor_registry.monitor_count,
                monitor_count_getter=lambda: monitor_registry.monitor_count,
            ).run()
        )
    )
    tasks.append(
        asyncio.create_task(
            BackupTask(
                mongodb_uri=settings.mongodb_uri,
                backup_dir="./backups/mongo",
                notifier=notifier,
            ).run()
        )
    )
    tasks.append(asyncio.create_task(_health_server()))

    # Graceful shutdown on SIGINT / SIGTERM
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: _shutdown(tasks, client, repo))

    logger.info(
        "phicube_running",
        monitor_count=monitor_registry.monitor_count,
        runtime_monitor_auto_sync=settings.runtime_monitor_auto_sync,
    )

    try:
        await asyncio.gather(*tasks)
    finally:
        await monitor_registry.close()
        await client.close()
        await repo.close()
        logger.info("phicube_stopped")


def _shutdown(
    tasks: list[asyncio.Task],
    client: Any,
    repo: MongoRepository,
) -> None:
    logger.info("shutdown_signal_received")
    for task in tasks:
        task.cancel()


def entrypoint() -> None:
    """CLI entry point registered in pyproject.toml."""
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(_main())


if __name__ == "__main__":
    entrypoint()
