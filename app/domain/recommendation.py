"""
Modelos de dominio: Recommendation, Action, ExpectedEffect.
"""
from typing import Any, Literal

from pydantic import BaseModel, Field


RecommendationStatus = Literal["pending", "applied", "discarded", "expired", "evaluated"]


class Action(BaseModel):
    """Una acción concreta que el agente propone ejecutar."""

    tool: str = Field(..., description="Nombre de la herramienta del agente")
    params: dict[str, Any] = Field(default_factory=dict, description="Parámetros de la herramienta")


class ExpectedEffect(BaseModel):
    """Efecto esperado comparando antes y después de la acción (en el horizonte de búsqueda)."""

    avg_wait_before_min: float
    avg_wait_after_min: float
    abandonment_before_pct: float
    abandonment_after_pct: float
    horizon_min: int


class Recommendation(BaseModel):
    """Recomendación generada por el agente para una corrida."""

    id: str = Field(..., description="Identificador de la recomendación (p. ej. 'rec-0001')")
    run_id: str
    minute: int = Field(..., ge=0)
    status: RecommendationStatus = "pending"
    motive: str = Field(..., description="Motivo de la recomendación en lenguaje natural")
    actions: list[Action] = Field(default_factory=list)
    summary: str = Field(..., description="Resumen de las acciones en lenguaje natural")
    expected_effect: ExpectedEffect | None = None
