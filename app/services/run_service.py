"""
RunService — gestión de corridas en memoria + ciclo del agente.
Las corridas activas viven en RunRegistry (dict protegido por Lock).
Se persisten al terminar.

PROVISIONAL: el registro en memoria solo soporta un proceso de Uvicorn sin --workers.
"""
from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime
from typing import Literal

from app.domain.scenario import Scenario
from app.domain.recommendation import Recommendation, Action
from app.domain.results import KpiSnapshot, RunResult, PhaseResult
from app.repositories.base import RunRepository, AuditRepository, ScenarioRepository
from app.simulation.engine import SimulationEngine
from app.simulation.state import build_state
import time

from app.agent.advisor import HeuristicAdvisor
from app.agent.audit import log_recommendation
from app.agent.planner import _apply_action

logger = logging.getLogger(__name__)

RunMode = Literal["base", "agent"]


class RunNotFound(Exception):
    pass


class InvalidRunState(Exception):
    pass


class _RunEntry:
    """Registro interno de una corrida activa."""

    def __init__(
        self,
        run_id: str,
        scenario: Scenario,
        engine: SimulationEngine,
        mode: RunMode,
    ) -> None:
        self.run_id = run_id
        self.scenario = scenario
        self.engine = engine
        self.mode = mode
        self.recommendations: list[Recommendation] = []
        self.rec_counter = 0
        self.last_recommendation_minute: int = -999
        self.finished: bool = False

    def next_rec_id(self) -> str:
        self.rec_counter += 1
        return f"rec-{self.rec_counter:04d}"


class RunRegistry:
    """Registro thread-safe de corridas activas en memoria."""

    def __init__(self) -> None:
        self._runs: dict[str, _RunEntry] = {}
        self._lock = threading.Lock()

    def add(self, entry: _RunEntry) -> None:
        with self._lock:
            self._runs[entry.run_id] = entry

    def get(self, run_id: str) -> _RunEntry | None:
        with self._lock:
            return self._runs.get(run_id)

    def remove(self, run_id: str) -> None:
        with self._lock:
            self._runs.pop(run_id, None)


# Registro global singleton (instanciado al importar)
_registry = RunRegistry()


def get_registry() -> RunRegistry:
    return _registry


class RunService:
    def __init__(
        self,
        scenario_repo: ScenarioRepository,
        run_repo: RunRepository,
        audit_repo: AuditRepository,
    ) -> None:
        self._scenario_repo = scenario_repo
        self._run_repo = run_repo
        self._audit_repo = audit_repo
        self._advisor = _build_advisor()

    # ------------------------------------------------------------------
    # Crear corrida
    # ------------------------------------------------------------------

    def create_run(
        self, scenario_id: str, mode: RunMode, seed: int | None = None
    ) -> str:
        sc = self._scenario_repo.get(scenario_id)
        if sc is None:
            from app.services.scenario_service import ScenarioNotFound
            raise ScenarioNotFound(f"Escenario '{scenario_id}' no encontrado.")

        effective_seed = seed if seed is not None else sc.seed
        state = build_state(sc, effective_seed)
        engine = SimulationEngine(sc, state)

        from datetime import timezone
        run_id = f"run-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
        entry = _RunEntry(run_id=run_id, scenario=sc, engine=engine, mode=mode)
        _registry.add(entry)
        logger.info("Corrida creada: %s (escenario=%s, modo=%s, semilla=%d)", run_id, scenario_id, mode, effective_seed)
        return run_id

    # ------------------------------------------------------------------
    # Avanzar la simulación
    # ------------------------------------------------------------------

    def step(self, run_id: str, minutes: int = 1) -> dict:
        """
        Avanza la corrida `minutes` minutos.
        En modo agente puede devolver una recomendación pendiente y pausar.
        """
        from app.config import get_settings
        settings = get_settings()

        entry = _registry.get(run_id)
        if entry is None:
            raise RunNotFound(f"Corrida '{run_id}' no encontrada.")
        if entry.finished:
            raise InvalidRunState(f"La corrida '{run_id}' ya terminó.")

        # En modo agente, verificar si hay pendientes antes de avanzar
        pending = [r for r in entry.recommendations if r.status == "pending"]
        if entry.mode == "agent" and len(pending) >= settings.max_pending_recommendations:
            snap = entry.engine.snapshot()
            return {"snapshot": snap, "recommendations": pending, "paused": True}

        snap = entry.engine.step(minutes)

        # Verificar si terminó
        if entry.engine.state.finished:
            entry.finished = True
            self._persist_result(entry)

        new_recs: list[Recommendation] = []
        if entry.mode == "agent" and not entry.finished:
            cooldown = settings.recommendation_cooldown
            current_min = entry.engine.state.current_minute
            if current_min - entry.last_recommendation_minute >= cooldown:
                t0 = time.perf_counter()
                recs = self._advisor.recommend(entry.engine.state, entry.scenario)
                response_time_s = round(time.perf_counter() - t0, 4)
                for rec in recs:
                    rec.id = entry.next_rec_id()
                    rec.run_id = run_id
                    entry.recommendations.append(rec)
                    entry.last_recommendation_minute = current_min
                    new_recs.append(rec)
                    kpis_before = {
                        "global_avg_wait_min": snap.global_avg_wait_min,
                        "global_abandonment_rate": snap.global_abandonment_rate,
                        "response_time_s": response_time_s,
                        "advisor_provider": settings.advisor_provider,
                    }
                    log_recommendation(self._audit_repo, run_id, rec, kpis_before)

        all_pending = [r for r in entry.recommendations if r.status == "pending"]
        return {
            "snapshot": snap,
            "recommendations": new_recs,
            "all_pending": all_pending,
            "paused": len(all_pending) >= settings.max_pending_recommendations,
            "finished": entry.finished,
        }

    def run_to_end(self, run_id: str) -> dict:
        """Avanza hasta el final (solo modo base o agente con aprobación automática)."""
        entry = _registry.get(run_id)
        if entry is None:
            raise RunNotFound(f"Corrida '{run_id}' no encontrada.")
        if entry.finished:
            raise InvalidRunState(f"La corrida '{run_id}' ya terminó.")
        if entry.mode == "agent":
            pending = [r for r in entry.recommendations if r.status == "pending"]
            if pending:
                raise InvalidRunState("Hay recomendaciones pendientes; resuélvalas antes de continuar.")

        while not entry.engine.state.finished:
            entry.engine.step(1)
            if entry.engine.state.finished:
                break

        entry.finished = True
        self._persist_result(entry)
        snap = entry.engine.snapshot()
        return {"snapshot": snap, "finished": True}

    # ------------------------------------------------------------------
    # Estado y resultados
    # ------------------------------------------------------------------

    def get_state(self, run_id: str) -> KpiSnapshot:
        entry = _registry.get(run_id)
        if entry is None:
            raise RunNotFound(f"Corrida '{run_id}' no encontrada.")
        return entry.engine.snapshot()

    def get_recommendations(self, run_id: str) -> list[Recommendation]:
        entry = _registry.get(run_id)
        if entry is None:
            # Intentar cargar desde persistencia
            raise RunNotFound(f"Corrida '{run_id}' no encontrada en memoria.")
        return entry.recommendations

    def get_result(self, run_id: str) -> RunResult | None:
        return self._run_repo.get_result(run_id)

    def get_audit(self, run_id: str) -> list[dict]:
        return self._audit_repo.read(run_id)

    # ------------------------------------------------------------------
    # Aplicar / descartar recomendaciones
    # ------------------------------------------------------------------

    def apply_recommendation(
        self, run_id: str, rec_id: str, actions_override: list[Action] | None = None
    ) -> KpiSnapshot:
        entry = _registry.get(run_id)
        if entry is None:
            raise RunNotFound(f"Corrida '{run_id}' no encontrada.")

        rec = next((r for r in entry.recommendations if r.id == rec_id), None)
        if rec is None or rec.status != "pending":
            raise InvalidRunState(f"Recomendación '{rec_id}' no está pendiente.")

        actions = actions_override if actions_override else rec.actions
        for action in actions:
            _apply_action(entry.engine.state, entry.scenario, action)

        rec.status = "applied"
        snap = entry.engine.snapshot()
        kpis_after = {"global_avg_wait_min": snap.global_avg_wait_min,
                      "global_abandonment_rate": snap.global_abandonment_rate}
        log_recommendation(self._audit_repo, run_id, rec, {}, kpis_after)
        return snap

    def discard_recommendation(self, run_id: str, rec_id: str) -> None:
        entry = _registry.get(run_id)
        if entry is None:
            raise RunNotFound(f"Corrida '{run_id}' no encontrada.")

        rec = next((r for r in entry.recommendations if r.id == rec_id), None)
        if rec is None or rec.status != "pending":
            raise InvalidRunState(f"Recomendación '{rec_id}' no está pendiente.")

        rec.status = "discarded"
        log_recommendation(self._audit_repo, run_id, rec, {})

    # ------------------------------------------------------------------
    # Persistencia al terminar
    # ------------------------------------------------------------------

    def _persist_result(self, entry: _RunEntry) -> None:
        state = entry.engine.state
        scenario = entry.scenario

        phase_results: list[PhaseResult] = []
        # Construir resultados por fase desde la historia
        phases = scenario.phases
        elapsed = 0
        for i, phase in enumerate(phases):
            phase_minutes = [
                h for h in state.history
                if elapsed <= h["minute"] < elapsed + phase.duration_min
            ]
            if phase_minutes:
                avg_wait = sum(m["global_avg_wait_min"] for m in phase_minutes) / len(phase_minutes)
                max_queue = max(m["global_max_queue"] for m in phase_minutes)
                avg_abd = sum(m["global_abandonment_rate"] for m in phase_minutes) / len(phase_minutes)
                avg_occ = sum(m["global_occupancy"] for m in phase_minutes) / len(phase_minutes)
            else:
                avg_wait = max_queue = avg_abd = avg_occ = 0.0

            # Calcular totales de la fase desde el estado de los puestos
            total_served = sum(ss.total_served for ss in state.stands.values())
            total_abandoned = sum(ss.total_abandoned for ss in state.stands.values())

            phase_results.append(PhaseResult(
                phase=phase.name,
                avg_wait_min=round(avg_wait, 2),
                max_queue=max_queue,
                abandonment_rate=round(avg_abd, 4),
                occupancy=round(avg_occ, 4),
            ))
            elapsed += phase.duration_min

        total_served = sum(ss.total_served for ss in state.stands.values())
        total_abandoned = sum(ss.total_abandoned for ss in state.stands.values())
        total_wait = sum(ss.total_wait_min for ss in state.stands.values())
        global_avg_wait = total_wait / max(total_served, 1)
        global_abd = total_abandoned / max(total_served + total_abandoned, 1)

        result = RunResult(
            run_id=entry.run_id,
            scenario_id=scenario.id,
            mode=entry.mode,
            seed=state.seed,
            total_minutes=state.current_minute,
            phases=phase_results,
            global_avg_wait_min=round(global_avg_wait, 2),
            global_abandonment_rate=round(global_abd, 4),
            total_served=total_served,
            total_abandoned=total_abandoned,
        )
        self._run_repo.save_result(result)
        logger.info("Corrida persistida: %s", entry.run_id)


def _build_advisor():
    """Construye el asesor según ADVISOR_PROVIDER."""
    from app.config import get_settings
    settings = get_settings()
    if settings.advisor_provider == "orchestrate" and settings.orchestrate_url and settings.orchestrate_api_key:
        from app.agent.orchestrate_advisor import OrchestrateAdvisor
        logger.info("Usando OrchestrateAdvisor (IBM watsonx Orchestrate).")
        return OrchestrateAdvisor(
            url=settings.orchestrate_url,
            api_key=settings.orchestrate_api_key,
            agent_id=settings.orchestrate_agent_id,
            timeout=settings.orchestrate_timeout,
        )
    logger.info("Usando HeuristicAdvisor (asesor local provisional).")
    return HeuristicAdvisor()
