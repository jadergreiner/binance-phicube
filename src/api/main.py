"""Aplicação FastAPI base do dashboard de consulta de posições."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib import import_module
from pathlib import Path
from typing import Any

FastAPI = import_module("fastapi").FastAPI
get_settings = import_module("src.config.settings").get_settings
DashboardModule = import_module("src.dashboard")
FileResponse = import_module("fastapi.responses").FileResponse
PositionStream = import_module("src.dashboard.stream").PositionStream
positions_router = import_module("src.api.routes.positions").router
performance_router = import_module("src.api.routes.performance").router
health_router = import_module("src.api.routes.health").router
backtest_router = import_module("src.api.routes.backtest").router
StaticFiles = import_module("fastapi.staticfiles").StaticFiles
AdaptiveUpdater = DashboardModule.AdaptiveUpdater
DashboardClient = DashboardModule.DashboardClient
MongoRepository = import_module("src.storage.repository").MongoRepository
get_logger = import_module("src.monitoring.logger").get_logger

logger = get_logger(__name__)

_STATIC_DIR = Path(__file__).resolve().parents[1] / "frontend" / "static"


class _OfflinePositionStream:
    def __init__(self) -> None:
        self.on_update = None

    def get_positions(self) -> list[Any]:
        return []

    def get_status(self) -> str:
        return "offline"

    async def stop(self, *, status: str = "offline") -> None:
        return None


async def _safe_call(coro: Any, *, warning_message: str) -> bool:
    try:
        await coro
        return True
    except Exception as exc:
        logger.warning(warning_message, error=str(exc))
        return False


@asynccontextmanager
async def lifespan(app: Any) -> AsyncIterator[None]:
    """Gerencia o ciclo de vida compartilhado do dashboard."""
    settings = get_settings()
    dashboard_client = DashboardClient(settings)
    position_stream = PositionStream(dashboard_client)
    adaptive_updater = AdaptiveUpdater()
    try:
        repository = MongoRepository(settings.mongodb_uri, settings.mongodb_database)
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
    app.include_router(positions_router)
    app.include_router(performance_router)
    app.include_router(health_router)
    app.include_router(backtest_router)

    @app.get("/")
    async def read_index() -> FileResponse:
        """Entrega a página principal do dashboard."""
        return FileResponse(_STATIC_DIR / "index.html", media_type="text/html")

    return app


app = create_app()
