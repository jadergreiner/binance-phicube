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
StaticFiles = import_module("fastapi.staticfiles").StaticFiles
AdaptiveUpdater = DashboardModule.AdaptiveUpdater
DashboardClient = DashboardModule.DashboardClient

_STATIC_DIR = Path(__file__).resolve().parents[1] / "frontend" / "static"


@asynccontextmanager
async def lifespan(app: Any) -> AsyncIterator[None]:
    """Gerencia o ciclo de vida compartilhado do dashboard."""
    settings = get_settings()
    dashboard_client = DashboardClient(settings)
    position_stream = PositionStream(dashboard_client)
    adaptive_updater = AdaptiveUpdater()

    app.state.settings = settings
    app.state.dashboard_client = dashboard_client
    app.state.position_stream = position_stream
    app.state.stream = position_stream
    app.state.adaptive_updater = adaptive_updater

    try:
        await dashboard_client.connect()
        await position_stream.start()
        await adaptive_updater.start(position_stream)
        yield
    finally:
        await adaptive_updater.stop()
        await position_stream.stop()
        await dashboard_client.close()


def create_app() -> Any:
    """Cria a aplicação FastAPI do dashboard."""
    app = FastAPI(
        title="Binance Phicube Dashboard API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")
    app.include_router(positions_router)

    @app.get("/")
    async def read_index() -> FileResponse:
        """Entrega a página principal do dashboard."""
        return FileResponse(_STATIC_DIR / "index.html", media_type="text/html")

    return app


app = create_app()
