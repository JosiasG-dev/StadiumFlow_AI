"""
Generación de llegadas por fase y perfil.
La palanca de anticipación (anticipation_share) desplaza parte de la demanda
de medio_tiempo a los últimos 5 minutos del primer_tiempo.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.scenario import Scenario
    from app.simulation.state import SimState


# Minutos finales del primer tiempo que reciben la demanda anticipada
ANTICIPATION_WINDOW_MIN = 5


def _phase_at_minute(phases: list, minute: int) -> tuple[int, int]:
    """
    Devuelve (índice de fase, minuto dentro de la fase) para el minuto global dado.
    """
    elapsed = 0
    for i, phase in enumerate(phases):
        if minute < elapsed + phase.duration_min:
            return i, minute - elapsed
        elapsed += phase.duration_min
    # Fuera del rango: devolver la última fase
    return len(phases) - 1, minute - (elapsed - phases[-1].duration_min)


def arrival_rate(scenario: "Scenario", phase_index: int) -> float:
    """
    Tasa de llegadas por minuto para la fase indicada.
    = attendance × purchase_prob / duration_min
    """
    phase = scenario.phases[phase_index]
    return scenario.attendance * phase.purchase_prob / phase.duration_min


def generate_arrivals(state: "SimState", scenario: "Scenario") -> list[tuple[str, str]]:
    """
    Genera las llegadas del minuto actual.
    Devuelve lista de (sector_id, perfil_nombre).

    Considera:
    - Fase actual y su purchase_prob
    - Anticipation_share: en los últimos ANTICIPATION_WINDOW_MIN del primer_tiempo,
      añade una fracción de la demanda del medio_tiempo.
    """
    phases = scenario.phases
    phase_idx = state.phase_index
    phase_min = state.phase_minute

    phase = phases[phase_idx]
    base_rate = scenario.attendance * phase.purchase_prob / phase.duration_min

    # Palanca de anticipación (Could): solo aplica en los últimos minutos del primer_tiempo
    extra_rate = 0.0
    if (
        phase.name == "primer_tiempo"
        and scenario.anticipation_share > 0.0
        and phase_min >= phase.duration_min - ANTICIPATION_WINDOW_MIN
    ):
        halftime_phase = next(p for p in phases if p.name == "medio_tiempo")
        halftime_total = scenario.attendance * halftime_phase.purchase_prob
        extra_rate = (halftime_total * scenario.anticipation_share) / ANTICIPATION_WINDOW_MIN

    total_rate = base_rate + extra_rate

    arrivals: list[tuple[str, str]] = []
    for sector in scenario.sectors:
        sector_rate = total_rate * sector.share
        n = state.rng.gauss(sector_rate, max(sector_rate ** 0.5, 0.01))
        n = max(0, round(n))
        for _ in range(n):
            profile = _pick_profile(scenario, state)
            arrivals.append((sector.id, profile))

    return arrivals


def _pick_profile(scenario: "Scenario", state: "SimState") -> str:
    """Elige un perfil según su share usando el RNG del estado."""
    r = state.rng.random()
    cumulative = 0.0
    for profile in scenario.profiles:
        cumulative += profile.share
        if r <= cumulative:
            return profile.name
    return scenario.profiles[-1].name
