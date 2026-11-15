"""
Bitácora JSONL de recomendaciones del agente.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.repositories.base import AuditRepository
    from app.domain.recommendation import Recommendation


def log_recommendation(
    repo: "AuditRepository",
    run_id: str,
    rec: "Recommendation",
    kpis_before: dict,
    kpis_after: dict | None = None,
) -> None:
    """Escribe la recomendación y su resultado en la bitácora JSONL."""
    record = {
        "id": rec.id,
        "run_id": run_id,
        "minute": rec.minute,
        "status": rec.status,
        "motive": rec.motive,
        "summary": rec.summary,
        "actions": [a.model_dump() for a in rec.actions],
        "kpis_before": kpis_before,
        "kpis_after": kpis_after,
        "expected_effect": rec.expected_effect.model_dump() if rec.expected_effect else None,
    }
    repo.append(run_id, record)
