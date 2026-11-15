"""
Rutas de informes y comparaciones (API JSON).
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.services.comparison_service import ComparisonService
from app.services.report_service import ReportService
from app.api.deps import get_comparison_service, get_report_service
from app.config import get_settings

router = APIRouter()
ComparisonServiceDep = Annotated[ComparisonService, Depends(get_comparison_service)]
ReportServiceDep = Annotated[ReportService, Depends(get_report_service)]


class ComparisonRequest(BaseModel):
    scenario_id: str
    replicas: int = Field(default=10, ge=1)
    seed: int | None = None

    def validated_replicas(self) -> int:
        settings = get_settings()
        if self.replicas > settings.max_replicas:
            raise ValueError(f"replicas no puede superar {settings.max_replicas}.")
        return self.replicas


@router.post("/comparisons", status_code=201)
def create_comparison(body: ComparisonRequest, svc: ComparisonServiceDep) -> dict:
    settings = get_settings()
    if body.replicas > settings.max_replicas:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail=f"replicas no puede superar {settings.max_replicas}.")
    seed = body.seed if body.seed is not None else settings.default_seed
    result = svc.compare(body.scenario_id, body.replicas, seed)
    return result.model_dump()


@router.get("/comparisons/{comparison_id}")
def get_comparison(comparison_id: str, svc: ComparisonServiceDep) -> dict:
    result = svc.get_comparison(comparison_id)
    if result is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Comparación no encontrada.")
    return result.model_dump()


@router.get("/comparisons/{comparison_id}/export")
def export_comparison(
    comparison_id: str,
    format: str = Query(default="json", pattern="^(csv|json|pdf)$"),
    report_svc: ReportServiceDep = None,
) -> Response:
    content, media_type = report_svc.export(comparison_id, format)  # type: ignore[arg-type]
    filename = f"comparison_{comparison_id}.{format}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
