"""
Elección de puesto por sector y redirecciones del agente.
Peso del puesto j para el sector i: w_ij = exp(−caminata_ij / τ), normalizado.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.scenario import Scenario, Stand, Sector
    from app.simulation.state import SimState

# Constante de decaimiento (minutos); configurable en Settings
TAU_DEFAULT = 2.0
WALK_MIN_PER_UNIT_DEFAULT = 0.01


def walk_time(sector: "Sector", stand: "Stand", walk_min_per_unit: float) -> float:
    """Tiempo de caminata entre sector y puesto (minutos)."""
    dx = stand.x - sector.x
    dy = stand.y - sector.y
    return math.sqrt(dx * dx + dy * dy) * walk_min_per_unit


def choose_stand(
    sector_id: str,
    profile_name: str,
    state: "SimState",
    scenario: "Scenario",
    tau: float = TAU_DEFAULT,
    walk_min_per_unit: float = WALK_MIN_PER_UNIT_DEFAULT,
) -> str:
    """
    Elige el puesto al que se dirige el aficionado.

    Si hay una redirección activa para el sector y el aficionado cumple con
    redirect_compliance, va directamente al puesto recomendado.
    De lo contrario, elige por peso de cercanía (sin ver las filas).
    """
    stand_state = state.stands
    sector = next(s for s in scenario.sectors if s.id == sector_id)

    # Comprobar redirección activa en alguno de los puestos
    for st_id, st_st in stand_state.items():
        if sector_id in st_st.redirections:
            target_id = st_st.redirections[sector_id]
            if state.rng.random() < state.redirect_compliance:
                # Verificar que el puesto destino existe
                if any(s.id == target_id for s in scenario.stands):
                    return target_id

    # Elección por proximidad con pesos exponenciales
    weights: list[float] = []
    stand_ids: list[str] = []
    for stand in scenario.stands:
        t = walk_time(sector, stand, walk_min_per_unit)
        weights.append(math.exp(-t / tau))
        stand_ids.append(stand.id)

    total_w = sum(weights)
    r = state.rng.random() * total_w
    cumulative = 0.0
    for sid, w in zip(stand_ids, weights):
        cumulative += w
        if r <= cumulative:
            return sid
    return stand_ids[-1]
