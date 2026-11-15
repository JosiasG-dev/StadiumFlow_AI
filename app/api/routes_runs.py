"""
Rutas de corridas (API JSON).
"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.domain.recommendation import Action
from app.services.run_service import RunService
from app.api.deps import get_run_service

router = APIRouter()
RunServiceDep = Annotated[RunService, Depends(get_run_service)]


class CreateRunRequest(BaseModel):
    scenario_id: str
    mode: str = Field(default="base", pattern="^(base|agent)$")
    seed: int | None = None


class StepRequest(BaseModel):
    minutes: int = Field(default=1, ge=1, le=15)


class ApplyRequest(BaseModel):
    actions_override: list[Action] | None = None


@router.post("", status_code=201)
def create_run(body: CreateRunRequest, svc: RunServiceDep) -> dict:
    run_id = svc.create_run(body.scenario_id, body.mode, body.seed)  # type: ignore[arg-type]
    return {"run_id": run_id}


@router.post("/{run_id}/step")
def step_run(run_id: str, body: StepRequest, svc: RunServiceDep) -> dict[str, Any]:
    result = svc.step(run_id, body.minutes)
    # Serializar snapshot a dict
    snap = result["snapshot"]
    return {
        "snapshot": snap.model_dump(),
        "recommendations": [r.model_dump() for r in result.get("recommendations", [])],
        "all_pending": [r.model_dump() for r in result.get("all_pending", [])],
        "paused": result.get("paused", False),
        "finished": result.get("finished", False),
    }


@router.post("/{run_id}/run-to-end")
def run_to_end(run_id: str, svc: RunServiceDep) -> dict:
    result = svc.run_to_end(run_id)
    snap = result["snapshot"]
    return {"snapshot": snap.model_dump(), "finished": result["finished"]}


@router.get("/{run_id}/state")
def get_state(run_id: str, svc: RunServiceDep) -> dict:
    snap = svc.get_state(run_id)
    return snap.model_dump()


@router.get("/{run_id}/result")
def get_result(run_id: str, svc: RunServiceDep) -> dict:
    result = svc.get_result(run_id)
    if result is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Resultado no encontrado.")
    return result.model_dump()


@router.get("/{run_id}/recommendations")
def get_recommendations(run_id: str, svc: RunServiceDep) -> list[dict]:
    recs = svc.get_recommendations(run_id)
    return [r.model_dump() for r in recs]


@router.post("/{run_id}/recommendations/{rec_id}/apply")
def apply_recommendation(run_id: str, rec_id: str, body: ApplyRequest, svc: RunServiceDep) -> dict:
    snap = svc.apply_recommendation(run_id, rec_id, body.actions_override)
    return snap.model_dump()


@router.post("/{run_id}/recommendations/{rec_id}/discard", status_code=204)
def discard_recommendation(run_id: str, rec_id: str, svc: RunServiceDep) -> None:
    svc.discard_recommendation(run_id, rec_id)


@router.get("/{run_id}/audit")
def get_audit(run_id: str, svc: RunServiceDep) -> list[dict]:
    return svc.get_audit(run_id)
