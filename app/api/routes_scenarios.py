"""
Rutas de escenarios (API JSON).
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.domain.scenario import Scenario
from app.services.scenario_service import ScenarioService
from app.api.deps import get_scenario_service

router = APIRouter()
ScenarioServiceDep = Annotated[ScenarioService, Depends(get_scenario_service)]


class DuplicateRequest(BaseModel):
    new_id: str = Field(..., min_length=3, max_length=40)
    new_name: str = Field(..., min_length=1, max_length=120)


@router.get("", response_model=list[Scenario])
def list_scenarios(svc: ScenarioServiceDep):
    return svc.list_scenarios()


@router.post("", response_model=Scenario, status_code=201)
def create_scenario(scenario: Scenario, svc: ScenarioServiceDep):
    return svc.create_scenario(scenario)


@router.get("/{scenario_id}", response_model=Scenario)
def get_scenario(scenario_id: str, svc: ScenarioServiceDep):
    return svc.get_scenario(scenario_id)


@router.put("/{scenario_id}", response_model=Scenario)
def update_scenario(scenario_id: str, scenario: Scenario, svc: ScenarioServiceDep):
    return svc.update_scenario(scenario_id, scenario)


@router.delete("/{scenario_id}", status_code=204)
def delete_scenario(scenario_id: str, svc: ScenarioServiceDep):
    svc.delete_scenario(scenario_id)


@router.post("/{scenario_id}/duplicate", response_model=Scenario, status_code=201)
def duplicate_scenario(scenario_id: str, body: DuplicateRequest, svc: ScenarioServiceDep):
    return svc.duplicate_scenario(scenario_id, body.new_id, body.new_name)
