"""
StadiumFlow AI — Punto de entrada de la aplicación FastAPI.
"""
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.api.errors import register_exception_handlers
from app.api.routes_scenarios import router as scenarios_router
from app.api.routes_runs import router as runs_router
from app.api.routes_agent import router as agent_router
from app.api.routes_reports import router as reports_router
from app.web.routes_pages import router as pages_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="StadiumFlow AI",
        description="Simulador de logística de zonas de alimentos y bebidas con agente de IA.",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # Asegurar que existan los directorios de datos
    for subdir in ("scenarios", "runs", "audit"):
        (settings.data_dir / subdir).mkdir(parents=True, exist_ok=True)

    # Archivos estáticos
    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Routers de API
    app.include_router(scenarios_router, prefix="/api/scenarios", tags=["Escenarios"])
    app.include_router(runs_router, prefix="/api/runs", tags=["Corridas"])
    app.include_router(agent_router, prefix="/api", tags=["Agente"])
    app.include_router(reports_router, prefix="/api", tags=["Informes"])

    # Rutas de páginas HTML
    app.include_router(pages_router)

    # Manejadores de excepciones
    register_exception_handlers(app)

    logger.info("StadiumFlow AI iniciado (entorno: %s)", settings.app_env)
    return app


app = create_app()
