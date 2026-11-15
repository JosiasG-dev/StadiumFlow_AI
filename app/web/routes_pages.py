"""
Rutas que devuelven HTML renderizado con Jinja2.
"""
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.api.deps import get_scenario_service, get_run_service
from app.services.scenario_service import ScenarioService
from app.services.run_service import RunService

router = APIRouter()

_templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(_templates_dir))

ScenarioServiceDep = Annotated[ScenarioService, Depends(get_scenario_service)]
RunServiceDep = Annotated[RunService, Depends(get_run_service)]


@router.get("/", response_class=HTMLResponse)
def home(request: Request, svc: ScenarioServiceDep):
    scenarios = svc.list_scenarios()
    return templates.TemplateResponse(request, "home.html", {"scenarios": scenarios})


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/scenarios", response_class=HTMLResponse)
def scenarios_list(request: Request, svc: ScenarioServiceDep):
    scenarios = svc.list_scenarios()
    return templates.TemplateResponse(request, "scenarios.html", {"scenarios": scenarios})


@router.get("/scenarios/new", response_class=HTMLResponse)
def scenario_new(request: Request):
    return templates.TemplateResponse(request, "scenario_form.html", {"scenario": None, "action": "crear"})


@router.get("/scenarios/{scenario_id}/edit", response_class=HTMLResponse)
def scenario_edit(scenario_id: str, request: Request, svc: ScenarioServiceDep):
    sc = svc.get_scenario(scenario_id)
    return templates.TemplateResponse(request, "scenario_form.html", {"scenario": sc, "action": "editar"})


@router.get("/simulation/{run_id}", response_class=HTMLResponse)
def simulation_panel(run_id: str, request: Request):
    return templates.TemplateResponse(request, "simulation.html", {"run_id": run_id})


@router.get("/agent/{run_id}", response_class=HTMLResponse)
def agent_panel(run_id: str, request: Request, svc: RunServiceDep):
    try:
        recs = svc.get_recommendations(run_id)
        audit = svc.get_audit(run_id)
    except Exception:
        recs = []
        audit = []
    return templates.TemplateResponse(request, "agent.html", {
        "run_id": run_id,
        "recommendations": recs,
        "audit": audit,
    })


@router.get("/reports", response_class=HTMLResponse)
def reports(request: Request, svc: ScenarioServiceDep):
    scenarios = svc.list_scenarios()
    return templates.TemplateResponse(request, "reports.html", {"scenarios": scenarios})


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    return templates.TemplateResponse(request, "settings.html", {})
