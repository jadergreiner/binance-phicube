"""Aplicação FastAPI base do dashboard de consulta de posições."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib import import_module
from pathlib import Path
from typing import Any

from src.common.decorators import _safe_call

FastAPI = import_module("fastapi").FastAPI
get_settings = import_module("src.config.settings").get_settings
DashboardModule = import_module("src.dashboard")
FileResponse = import_module("fastapi.responses").FileResponse
PlainTextResponse = import_module("fastapi.responses").PlainTextResponse
PositionStream = import_module("src.dashboard.stream").PositionStream
positions_router = import_module("src.api.routes.positions").router
performance_router = import_module("src.api.routes.performance").router
health_router = import_module("src.api.routes.health").router
backtest_router = import_module("src.api.routes.backtest").router
trades_router = import_module("src.api.routes.trades").router
onboarding_router = import_module("src.api.routes.onboarding").router
signals_router = import_module("src.api.routes.signals").router
symbols_router = import_module("src.api.routes.symbols").router
customers_router = import_module("src.api.routes.customers").router
auth_router = import_module("src.api.routes.auth").router
StaticFiles = import_module("fastapi.staticfiles").StaticFiles
AdaptiveUpdater = DashboardModule.AdaptiveUpdater
DashboardClient = DashboardModule.DashboardClient
MongoRepository = import_module("src.storage.repository").MongoRepository
get_logger = import_module("src.monitoring.logger").get_logger
get_metrics = import_module("src.monitoring.metrics").get_metrics

logger = get_logger(__name__)

_STATIC_DIR = Path(__file__).resolve().parents[1] / "frontend" / "static"


class _OfflinePositionStream:
    def __init__(self) -> None:
        self.on_update = None

    def get_positions(self) -> list[Any]:
        return []

    def get_status(self) -> str:
        return "offline"

    def get_account_equity_usdt(self) -> float | None:
        return None

    async def stop(self, *, status: str = "offline") -> None:
        return None


@asynccontextmanager
async def lifespan(app: Any) -> AsyncIterator[None]:
    """Gerencia o ciclo de vida compartilhado do dashboard."""
    settings = get_settings()
    dashboard_client = DashboardClient(settings)
    position_stream = PositionStream(dashboard_client, track_account_equity=True)
    adaptive_updater = AdaptiveUpdater()
    try:
        repository = MongoRepository(
            settings.mongodb_uri,
            settings.mongodb_database,
            trade_history_retention_days=settings.trade_history_retention_days,
        )
    except AttributeError:
        repository = None

    app.state.settings = settings
    app.state.dashboard_client = dashboard_client
    app.state.position_stream = position_stream
    app.state.stream = position_stream
    app.state.adaptive_updater = adaptive_updater
    app.state.startup_mode = "offline"
    app.state.repository = repository

    try:
        client_connected = await _safe_call(
            dashboard_client.connect(),
            warning_message="dashboard_api_client_connect_failed",
        )
        stream_started = await _safe_call(
            position_stream.start(),
            warning_message="dashboard_position_stream_start_failed",
        )
        stream_status = position_stream.get_status()
        stream_operational = stream_started and stream_status in {"online", "cached"}
        logger.info(
            "dashboard_lifecycle_start_decision",
            client_connected=client_connected,
            stream_started=stream_started,
            stream_status=stream_status,
            stream_operational=stream_operational,
        )

        if stream_operational:
            await _safe_call(
                adaptive_updater.start(position_stream),
                warning_message="dashboard_adaptive_updater_start_failed",
            )

        if not stream_operational:
            logger.warning(
                "dashboard_lifecycle_offline_fallback_applied",
                client_connected=client_connected,
                stream_started=stream_started,
                stream_status=stream_status,
            )
            offline_stream = _OfflinePositionStream()
            app.state.position_stream = offline_stream
            app.state.stream = offline_stream
            app.state.startup_mode = "offline"
        else:
            app.state.startup_mode = stream_status
            logger.info(
                "dashboard_lifecycle_start_success",
                startup_mode=app.state.startup_mode,
            )
        if not client_connected and stream_operational:
            logger.warning("dashboard_api_client_connected_in_fallback_mode")

        yield
    finally:
        await adaptive_updater.stop()
        await position_stream.stop()
        await dashboard_client.close()
        if repository is not None:
            await repository.close()


def create_app() -> Any:
    """Cria a aplicação FastAPI do dashboard."""
    app = FastAPI(
        title="Binance Phicube Dashboard API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")
    app.include_router(auth_router)  # Auth routes (public)
    app.include_router(health_router)  # Health (public)
    # Rotas protegidas via Depends(get_current_user) em cada route
    app.include_router(positions_router)
    app.include_router(performance_router)
    app.include_router(backtest_router)
    app.include_router(trades_router)
    app.include_router(onboarding_router)
    app.include_router(signals_router)
    app.include_router(symbols_router)
    app.include_router(customers_router)

    @app.get("/")
    async def read_index() -> FileResponse:
        """Entrega a página principal do dashboard."""
        return FileResponse(_STATIC_DIR / "index.html", media_type="text/html")

    @app.get("/metrics", response_class=PlainTextResponse)
    async def metrics_endpoint() -> str:
        """
        Endpoint de métricas Prometheus (SPEC_032).

        Retorna todas as métricas no formato Prometheus.
        Se o módulo de métricas não estiver inicializado, retorna string vazia.
        """
        return get_metrics()

    return app


app = create_app()
