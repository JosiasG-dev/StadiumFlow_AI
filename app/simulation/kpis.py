"""
Cálculo de indicadores (KPIs).
Este módulo es la única fuente de verdad para los cálculos de espera estimada
y ocupación; lo usan tanto el motor como el agente.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.scenario import Scenario
    from app.simulation.state import SimState, StandState
    from app.domain.results import KpiSnapshot, StandKpi

# Segundos de servicio para pedido_movil en ventana de recolección rápida
PICKUP_SERVICE_SECONDS = 15.0


def estimated_wait_min(stand_state: "StandState", scenario: "Scenario") -> float:
    """
    Espera estimada para el próximo aficionado que llegue a este puesto (minutos).
    = cola / (cajas_abiertas × tasa_servicio_en_personas_por_minuto)
    """
    if stand_state.registers_open == 0:
        return float("inf")

    # Calcular tasa de servicio promedio ponderada del puesto
    rate_per_register = _avg_service_rate(stand_state, scenario)
    if rate_per_register <= 0:
        return float("inf")

    total_rate = stand_state.registers_open * rate_per_register
    return len(stand_state.queue) / total_rate if total_rate > 0 else float("inf")


def _avg_service_rate(stand_state: "StandState", scenario: "Scenario") -> float:
    """Atenciones por minuto por caja (promedio ponderado de perfiles en cola)."""
    if not stand_state.queue:
        # Sin cola: usar la tasa promedio de todos los perfiles
        total_weight = 0.0
        total_rate = 0.0
        for p in scenario.profiles:
            rate = 60.0 / p.service_seconds
            total_rate += rate * p.share
            total_weight += p.share
        return total_rate / total_weight if total_weight > 0 else 1.0

    # Con cola: usar los perfiles de las personas en cola
    total = 0.0
    for _, profile_name, service_s in stand_state.queue:
        effective_s = service_s
        if profile_name == "pedido_movil" and stand_state.pickup_enabled:
            effective_s = PICKUP_SERVICE_SECONDS
        total += 60.0 / effective_s
    return total / len(stand_state.queue)


def occupancy(stand_state: "StandState", total_minutes: int) -> float:
    """
    Ocupación: tiempo que las cajas estuvieron ocupadas / tiempo disponible total.
    """
    if total_minutes <= 0 or stand_state.registers_open <= 0:
        return 0.0
    available = stand_state.registers_open * total_minutes
    return min(stand_state.total_service_time_min / available, 1.0)


def density(stand_state: "StandState", scenario: "Scenario") -> float:
    """
    Densidad en el pasillo: (cola + en tránsito) / capacidad de la zona.
    """
    stand_cfg = next((s for s in scenario.stands if s.id == stand_state.stand_id), None)
    if stand_cfg is None or stand_cfg.zone_capacity <= 0:
        return 0.0
    total_people = len(stand_state.queue) + stand_state.transit_count
    return total_people / stand_cfg.zone_capacity


def snapshot(state: "SimState", scenario: "Scenario") -> "KpiSnapshot":
    """Genera un KpiSnapshot del estado actual."""
    from app.domain.results import KpiSnapshot, StandKpi

    stand_kpis: list[StandKpi] = []
    total_served = 0
    total_abandoned = 0
    total_wait = 0.0
    total_occupancy = 0.0
    total_revenue = 0.0
    max_queue = 0

    elapsed = state.current_minute - _phase_start_minute(state, scenario)
    elapsed = max(elapsed, 1)

    for stand_cfg in scenario.stands:
        ss = state.stands[stand_cfg.id]
        est_wait = estimated_wait_min(ss, scenario)
        occ = occupancy(ss, elapsed)
        dens = density(ss, scenario)
        served = ss.total_served
        abandoned = ss.total_abandoned
        abd_rate = abandoned / max(served + abandoned, 1)
        avg_wait = ss.total_wait_min / max(served, 1)
        rev = served * stand_cfg.avg_ticket

        stand_kpis.append(StandKpi(
            stand_id=stand_cfg.id,
            queue_length=len(ss.queue),
            avg_wait_min=round(avg_wait, 2),
            max_wait_min=round(ss.max_wait_min, 2),
            abandonment_rate=round(abd_rate, 4),
            occupancy=round(occ, 4),
            density=round(dens, 4),
            registers_open=ss.registers_open,
            staff=ss.staff,
            estimated_wait_min=round(min(est_wait, 999.0), 2),
            revenue=round(rev, 2),
        ))

        total_served += served
        total_abandoned += abandoned
        total_wait += ss.total_wait_min
        total_occupancy += occ
        total_revenue += rev
        if len(ss.queue) > max_queue:
            max_queue = len(ss.queue)

    n_stands = len(scenario.stands)
    global_avg_wait = total_wait / max(total_served, 1)
    global_abd = total_abandoned / max(total_served + total_abandoned, 1)
    global_occ = total_occupancy / max(n_stands, 1)

    # Cuando la simulación termina, phase_index puede salirse del rango
    safe_phase_idx = min(state.phase_index, len(scenario.phases) - 1)
    phase_name = scenario.phases[safe_phase_idx].name

    return KpiSnapshot(
        minute=state.current_minute,
        phase=phase_name,
        stands=stand_kpis,
        global_avg_wait_min=round(global_avg_wait, 2),
        global_max_queue=max_queue,
        global_abandonment_rate=round(global_abd, 4),
        global_occupancy=round(global_occ, 4),
        global_revenue=round(total_revenue, 2),
    )


def _phase_start_minute(state: "SimState", scenario: "Scenario") -> int:
    """Minuto global en que empezó la fase actual."""
    elapsed = 0
    for i, phase in enumerate(scenario.phases):
        if i == state.phase_index:
            return elapsed
        elapsed += phase.duration_min
    return elapsed
