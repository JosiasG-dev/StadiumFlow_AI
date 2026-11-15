"""
ComparisonService — comparación base vs. agente con N réplicas.
"""
from __future__ import annotations

import logging
import math
import uuid
from typing import TYPE_CHECKING

from app.domain.results import ComparisonResult, ReplicaResult, PhaseAggregates, RunResult
from app.repositories.base import ScenarioRepository, RunRepository, AuditRepository

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ComparisonService:
    def __init__(
        self,
        scenario_repo: ScenarioRepository,
        run_repo: RunRepository,
        audit_repo: AuditRepository,
    ) -> None:
        self._scenario_repo = scenario_repo
        self._run_repo = run_repo
        self._audit_repo = audit_repo

    def compare(self, scenario_id: str, replicas: int, base_seed: int) -> ComparisonResult:
        """
        Ejecuta `replicas` pares (base, agente automático) con semillas consecutivas
        y agrega los resultados.
        Modo agente: aprobación automática (para evaluación de potencial, no corrida interactiva).
        """
        from app.services.scenario_service import ScenarioNotFound

        sc = self._scenario_repo.get(scenario_id)
        if sc is None:
            raise ScenarioNotFound(f"Escenario '{scenario_id}' no encontrado.")

        seeds = [base_seed + i for i in range(replicas)]
        replica_results: list[ReplicaResult] = []

        for seed in seeds:
            base_result = self._run_single(sc, "base", seed, auto_apply=False)
            agent_result = self._run_single(sc, "agent", seed, auto_apply=True)
            replica_results.append(ReplicaResult(seed=seed, base=base_result, agent=agent_result))

        # Agregar por fase
        phase_names = [p.name for p in sc.phases]
        phase_aggregates: list[PhaseAggregates] = []
        for phase_name in phase_names:
            base_waits = [
                _phase_metric(r.base, phase_name, "avg_wait_min") for r in replica_results
            ]
            agent_waits = [
                _phase_metric(r.agent, phase_name, "avg_wait_min") for r in replica_results
            ]
            base_abds = [
                _phase_metric(r.base, phase_name, "abandonment_rate") for r in replica_results
            ]
            halftime_reduction: float | None = None
            if phase_name == "medio_tiempo" and base_waits and agent_waits:
                bw = _mean(base_waits)
                aw = _mean(agent_waits)
                if bw > 0:
                    halftime_reduction = round((bw - aw) / bw * 100, 1)

            phase_aggregates.append(PhaseAggregates(
                phase=phase_name,
                avg_wait_mean=round(_mean(base_waits), 2),
                avg_wait_std=round(_std(base_waits), 2),
                abandonment_mean=round(_mean(base_abds), 4),
                abandonment_std=round(_std(base_abds), 4),
                halftime_wait_reduction_pct=halftime_reduction,
            ))

        # Reducción global
        base_global_waits = [r.base.global_avg_wait_min for r in replica_results]
        agent_global_waits = [r.agent.global_avg_wait_min for r in replica_results]
        bw_mean = _mean(base_global_waits)
        aw_mean = _mean(agent_global_waits)
        global_wait_reduction = round((bw_mean - aw_mean) / max(bw_mean, 0.01) * 100, 1)

        base_global_abds = [r.base.global_abandonment_rate for r in replica_results]
        agent_global_abds = [r.agent.global_abandonment_rate for r in replica_results]
        ba_mean = _mean(base_global_abds)
        aa_mean = _mean(agent_global_abds)
        global_abd_reduction = round((ba_mean - aa_mean) / max(ba_mean, 0.001) * 100, 1)

        comp_id = uuid.uuid4().hex[:8]
        result = ComparisonResult(
            id=comp_id,
            scenario_id=scenario_id,
            replicas=replicas,
            seeds=seeds,
            phase_aggregates=phase_aggregates,
            global_avg_wait_reduction_pct=global_wait_reduction,
            global_abandonment_reduction_pct=global_abd_reduction,
            replica_results=replica_results,
        )
        self._run_repo.save_comparison(result)
        return result

    def _run_single(self, scenario, mode: str, seed: int, auto_apply: bool) -> RunResult:
        """Corre una simulación completa en memoria y devuelve el RunResult."""
        from app.simulation.engine import SimulationEngine
        from app.simulation.state import build_state
        from app.agent.advisor import HeuristicAdvisor
        from app.agent.planner import _apply_action
        from app.domain.results import RunResult, PhaseResult
        from app.config import get_settings
        settings = get_settings()

        state = build_state(scenario, seed)
        engine = SimulationEngine(scenario, state)
        advisor = HeuristicAdvisor() if mode == "agent" else None
        last_rec_minute = -999

        while not engine.state.finished:
            engine.step(1)
            if advisor and auto_apply:
                current_min = engine.state.current_minute
                if current_min - last_rec_minute >= settings.recommendation_cooldown:
                    recs = advisor.recommend(engine.state, scenario)
                    for rec in recs:
                        for action in rec.actions:
                            try:
                                _apply_action(engine.state, scenario, action)
                            except Exception as exc:
                                logger.debug("Acción omitida en comparación: %s", exc)
                    if recs:
                        last_rec_minute = current_min

        state_final = engine.state
        phases = scenario.phases
        phase_results: list[PhaseResult] = []
        elapsed = 0
        for phase in phases:
            phase_minutes = [
                h for h in state_final.history
                if elapsed <= h["minute"] < elapsed + phase.duration_min
            ]
            avg_wait = _mean([m["global_avg_wait_min"] for m in phase_minutes]) if phase_minutes else 0.0
            max_queue = max((m["global_max_queue"] for m in phase_minutes), default=0)
            avg_abd = _mean([m["global_abandonment_rate"] for m in phase_minutes]) if phase_minutes else 0.0
            avg_occ = _mean([m["global_occupancy"] for m in phase_minutes]) if phase_minutes else 0.0
            phase_results.append(PhaseResult(
                phase=phase.name,
                avg_wait_min=round(avg_wait, 2),
                max_queue=max_queue,
                abandonment_rate=round(avg_abd, 4),
                occupancy=round(avg_occ, 4),
            ))
            elapsed += phase.duration_min

        total_served = sum(ss.total_served for ss in state_final.stands.values())
        total_abandoned = sum(ss.total_abandoned for ss in state_final.stands.values())
        total_wait = sum(ss.total_wait_min for ss in state_final.stands.values())
        global_avg_wait = total_wait / max(total_served, 1)
        global_abd = total_abandoned / max(total_served + total_abandoned, 1)

        import uuid as _uuid
        run_id = f"cmp-{seed}-{mode}-{_uuid.uuid4().hex[:4]}"
        return RunResult(
            run_id=run_id,
            scenario_id=scenario.id,
            mode=mode,
            seed=seed,
            total_minutes=state_final.current_minute,
            phases=phase_results,
            global_avg_wait_min=round(global_avg_wait, 2),
            global_abandonment_rate=round(global_abd, 4),
            total_served=total_served,
            total_abandoned=total_abandoned,
        )

    def get_comparison(self, comparison_id: str) -> ComparisonResult | None:
        return self._run_repo.get_comparison(comparison_id)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    variance = sum((v - m) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(variance)


def _phase_metric(result: RunResult, phase_name: str, metric: str) -> float:
    for p in result.phases:
        if p.phase == phase_name:
            return getattr(p, metric, 0.0)
    return 0.0
