"""
StadiumFlow AI — Configuración de la aplicación.
Lee variables de entorno con pydantic-settings.
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    host: str = "127.0.0.1"
    port: int = 8000
    data_dir: Path = Path("./data")

    default_seed: int = 42
    default_replicas: int = 10
    max_replicas: int = 30

    # Parámetros del agente
    advisor_provider: str = "heuristic"
    orchestrate_url: str = ""
    orchestrate_api_key: str = ""
    orchestrate_agent_id: str = ""
    orchestrate_timeout: int = 10
    # Penalización de abandono en la función de puntuación del planificador
    abandonment_penalty: float = 8.0
    # Mejora mínima relativa para recomendar (10 %)
    recommendation_threshold: float = 0.10
    # Horizonte de búsqueda anticipada (minutos simulados)
    lookahead_horizon: int = 10
    # Frecuencia mínima entre recomendaciones (minutos simulados)
    recommendation_cooldown: int = 3
    # Máximo de recomendaciones pendientes simultáneas
    max_pending_recommendations: int = 3

    # Umbrales del mapa de calor (espera estimada en minutos)
    heatmap_green_max: float = 3.0
    heatmap_yellow_max: float = 6.0

    # Constante de decaimiento para elección de puesto
    routing_tau: float = 2.0
    # Minutos de caminata por unidad de distancia SVG
    walk_min_per_unit: float = 0.01


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
