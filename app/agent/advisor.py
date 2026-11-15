"""
Protocolo Advisor e implementación HeuristicAdvisor.
HeuristicAdvisor es la implementación provisional del MVP (sin LLM).
Compatible con migración a watsonx Orchestrate (OrchestrateAdvisor en v2).

IMPLEMENTACIÓN PROVISIONAL: agente local de reglas y simulación anticipada.
Compatible con migración a watsonx Orchestrate (OrchestrateAdvisor en v2).
"""
from __future__ import annotations

import logging
from typing import Protocol, TYPE_CHECKING, runtime_checkable

from app.agent import planner, explainer
from app.agent.planner import _apply_action
from app.simulation.state import clone_state
from app.simulation import kpis as kpi_module

if TYPE_CHECKING:
    from app.domain.scenario import Scenario
    from app.simulation.state import SimState
    from app.domain.recommendation import Recommendation

logger = logging.getLogger(__name__)


@runtime_checkable
class Advisor(Protocol):
    def recommend(self, state: "SimState", scenario: "Scenario") -> list["Recommendation"]: ...


class HeuristicAdvisor:
    """
    Agente local determinista basado en búsqueda anticipada.
    PROVISIONAL: en v2 se reemplaza por OrchestrateAdvisor.
    """

    def recommend(self, state: "SimState", scenario: "Scenario") -> list["Recommendation"]:
        from app.config import get_settings
        from app.domain.recommendation import Recommendation, ExpectedEffect

        settings = get_settings()
        horizon = settings.lookahead_horizon

        actions = planner.plan(state, scenario, lookahead=horizon)
        if not actions:
            return []

        # Calcular efecto esperado
        state_before = clone_state(state)
        state_after = clone_state(state)
        for action in actions:
            try:
                _apply_action(state_after, scenario, action)
            except Exception as exc:
                logger.warning("No se pudo aplicar acción para efecto esperado: %s", exc)
                return []

        snap_before = kpi_module.snapshot(state_before, scenario)
        snap_after = kpi_module.snapshot(state_after, scenario)

        abd_before = snap_before.global_abandonment_rate * 100
        abd_after = snap_after.global_abandonment_rate * 100

        expected_effect = ExpectedEffect(
            avg_wait_before_min=snap_before.global_avg_wait_min,
            avg_wait_after_min=snap_after.global_avg_wait_min,
            abandonment_before_pct=round(abd_before, 1),
            abandonment_after_pct=round(abd_after, 1),
            horizon_min=horizon,
        )

        motive, summary = explainer.build_recommendation_text(actions, state, scenario, expected_effect)

        rec_id = f"rec-{state.current_minute:04d}"
        rec = Recommendation(
            id=rec_id,
            run_id=state.scenario_id,  # se sobreescribe en RunService con el run_id real
            minute=state.current_minute,
            status="pending",
            motive=motive,
            actions=actions,
            summary=summary,
            expected_effect=expected_effect,
        )
        return [rec]
