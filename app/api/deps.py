"""
Inyección de dependencias: crea y cachea los servicios y repositorios.
"""
from functools import lru_cache

from app.config import get_settings
from app.repositories.json_repository import (
    JsonScenarioRepository,
    JsonRunRepository,
    JsonAuditRepository,
)
from app.services.scenario_service import ScenarioService
from app.services.run_service import RunService
from app.services.comparison_service import ComparisonService
from app.services.report_service import ReportService


@lru_cache
def _get_scenario_repo() -> JsonScenarioRepository:
    return JsonScenarioRepository(get_settings().data_dir)


@lru_cache
def _get_run_repo() -> JsonRunRepository:
    return JsonRunRepository(get_settings().data_dir)


@lru_cache
def _get_audit_repo() -> JsonAuditRepository:
    return JsonAuditRepository(get_settings().data_dir)


def get_scenario_service() -> ScenarioService:
    return ScenarioService(_get_scenario_repo())


def get_run_service() -> RunService:
    return RunService(_get_scenario_repo(), _get_run_repo(), _get_audit_repo())


def get_comparison_service() -> ComparisonService:
    return ComparisonService(_get_scenario_repo(), _get_run_repo(), _get_audit_repo())


def get_report_service() -> ReportService:
    return ReportService(_get_run_repo())
