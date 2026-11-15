"""
Planificador del agente: detecta cuellos, genera candidatos y evalúa con búsqueda anticipada.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.agent import tools as agent_tools
from app.simulation.state import clone_state
from app.simulation import kpis as kpi_module

if TYPE_CHECKING:
    from app.domain.scenario import Scenario
    from app.simulation.state import SimState
    from app.domain.recommendation import Action

logger = logging.getLogger(__name__)

# Constantes del planificador
SATURATION_WAIT_MIN = 3.0      # espera estimada > 3 min → saturado (umbral reducido para demo)
LOOKAHEAD_MIN = 10             # horizonte de búsqueda anticipada
IMPROVEMENT_THRESHOLD = 0.05   # 5 % de mejora relativa (antes 10 %)
HALFTIME_ALERT_MIN = 10        # minutos antes del medio tiempo para activar proactividad


def _score(state: "SimState", scenario: "Scenario", horizon: int) -> float:
    """
    Puntuación del estado tras `horizon` minutos: menor es mejor.
    Mide solo el incremento generado en el horizonte (no acumulado desde el inicio).
    score = Δespera_total + 8 × Δabandonos
    """
    from app.simulation.engine import SimulationEngine
    from app.config import get_settings
    settings = get_settings()

    engine = SimulationEngine(scenario, clone_state(state))

    # Capturar los contadores actuales ANTES de avanzar
    wait_before = sum(ss.total_wait_min for ss in engine.state.stands.values())
    abandoned_before = sum(ss.total_abandoned for ss in engine.state.stands.values())

    for _ in range(horizon):
        if engine.state.finished:
            break
        engine.step(1)

    wait_after = sum(ss.total_wait_min for ss in engine.state.stands.values())
    abandoned_after = sum(ss.total_abandoned for ss in engine.state.stands.values())

    delta_wait = max(wait_after - wait_before, 0.0)
    delta_abandoned = max(abandoned_after - abandoned_before, 0)

    penalty = settings.abandonment_penalty
    return delta_wait + penalty * delta_abandoned


def _is_near_halftime(state: "SimState", scenario: "Scenario") -> bool:
    """
    Devuelve True si estamos DENTRO o a punto de entrar al medio tiempo.
    Cubre dos casos:
    - Estamos en los últimos HALFTIME_ALERT_MIN minutos del primer_tiempo.
    - Ya estamos en el medio_tiempo.
    """
    phases = scenario.phases
    elapsed = 0
    for phase in phases:
        if phase.name == "medio_tiempo":
            halftime_start = elapsed
            # Dentro del medio tiempo
            if state.current_minute >= halftime_start:
                halftime_end = halftime_start + phase.duration_min
                return state.current_minute < halftime_end
            # Justo antes del medio tiempo
            minutes_until = halftime_start - state.current_minute
            return 0 <= minutes_until <= HALFTIME_ALERT_MIN
        elapsed += phase.duration_min
    return False


def _detect_bottlenecks(
    state: "SimState", scenario: "Scenario"
) -> tuple[list[str], list[str]]:
    """
    Devuelve (saturados, subutilizados) listas de stand_id.
    Saturado: espera estimada > 6 min.
    Subutilizado: espera estimada < 1 min y cola vacía.
    """
    saturated: list[str] = []
    underused: list[str] = []
    for stand_cfg in scenario.stands:
        ss = state.stands[stand_cfg.id]
        est_wait = kpi_module.estimated_wait_min(ss, scenario)
        if est_wait > SATURATION_WAIT_MIN:
            saturated.append(stand_cfg.id)
        elif est_wait < 1.0 and len(ss.queue) == 0:
            underused.append(stand_cfg.id)
    return saturated, underused


def generate_candidates(
    state: "SimState", scenario: "Scenario"
) -> list[list["Action"]]:
    """
    Genera combinaciones candidatas de acciones para mejorar el estado.
    Devuelve lista de listas de Action.
    """
    from app.domain.recommendation import Action

    saturated, underused = _detect_bottlenecks(state, scenario)
    candidates: list[list[Action]] = []

    for sat_id in saturated:
        sat_ss = state.stands[sat_id]
        sat_cfg = next(s for s in scenario.stands if s.id == sat_id)

        # Candidato 1: Abrir cajas en el puesto saturado
        if sat_ss.registers_open < sat_cfg.registers_installed and sat_ss.registers_open < sat_ss.staff:
            candidates.append([Action(tool="abrir_cerrar_cajas", params={"stand_id": sat_id, "delta": 1})])

        # Candidato 2: Reasignar personal de un subutilizado al saturado
        for und_id in underused:
            und_ss = state.stands[und_id]
            if und_ss.staff > 1:
                actions = [
                    Action(tool="reasignar_personal", params={"origen_id": und_id, "destino_id": sat_id, "cantidad": 1}),
                ]
                # Si el traspaso permite abrir más cajas
                if sat_ss.registers_open < sat_cfg.registers_installed:
                    actions.append(Action(tool="abrir_cerrar_cajas", params={"stand_id": sat_id, "delta": 1}))
                candidates.append(actions)

        # Candidato 3: Redirigir el sector más cercano al saturado hacia el subutilizado con menos espera
        for und_id in underused:
            und_ss = state.stands[und_id]
            # Elegir el sector cuya mayor parte de tráfico va al saturado
            best_sector = _find_main_sector(sat_id, scenario)
            if best_sector:
                candidates.append([
                    Action(tool="redirigir_aficionados", params={"sector_id": best_sector, "stand_destino_id": und_id})
                ])

        # Candidato 4: Activar recolección rápida si hay pedido móvil
        mobile_profile = next((p for p in scenario.profiles if p.name == "pedido_movil"), None)
        if mobile_profile and mobile_profile.share >= 0.1 and not sat_ss.pickup_enabled:
            candidates.append([Action(tool="activar_recoleccion_rapida", params={"stand_id": sat_id})])

    return candidates


def _find_main_sector(stand_id: str, scenario: "Scenario") -> str | None:
    """Encuentra el sector con mayor afinidad (cercanía) hacia el puesto dado."""
    import math
    stand_cfg = next((s for s in scenario.stands if s.id == stand_id), None)
    if stand_cfg is None:
        return None

    best = None
    best_dist = float("inf")
    for sector in scenario.sectors:
        dx = stand_cfg.x - sector.x
        dy = stand_cfg.y - sector.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < best_dist:
            best_dist = dist
            best = sector.id
    return best


def plan(
    state: "SimState",
    scenario: "Scenario",
    lookahead: int = LOOKAHEAD_MIN,
) -> list["Action"] | None:
    """
    Ejecuta la búsqueda anticipada y devuelve la mejor combinación de acciones
    (o None si no hay mejora suficiente).
    """
    from app.config import get_settings
    settings = get_settings()
    threshold = settings.recommendation_threshold
    horizon = settings.lookahead_horizon

    # Proactividad: evaluar aunque no haya cuellos visibles si estamos cerca del medio tiempo
    near_halftime = _is_near_halftime(state, scenario)
    saturated, _ = _detect_bottlenecks(state, scenario)

    if not saturated and not near_halftime:
        return None

    # Puntuación sin intervención
    baseline_score = _score(state, scenario, horizon)

    candidates = generate_candidates(state, scenario)
    if not candidates:
        return None

    best_actions: list["Action"] | None = None
    best_score = baseline_score

    # Construcción voraz: probar cada candidato y conservar si mejora
    current_actions: list["Action"] = []
    current_state = clone_state(state)

    for candidate in candidates:
        # Aplicar el candidato a una copia del estado actual (voraz)
        test_state = clone_state(current_state)
        try:
            for action in candidate:
                _apply_action(test_state, scenario, action)
        except agent_tools.InvalidAction as exc:
            logger.debug("Candidato inválido descartado: %s", exc)
            continue

        score = _score(test_state, scenario, horizon)
        if score < best_score:
            best_score = score
            best_actions = current_actions + candidate
            current_state = test_state
            current_actions = best_actions

    if best_actions is None:
        return None

    improvement = (baseline_score - best_score) / max(baseline_score, 1.0)
    if improvement < threshold:
        return None

    return best_actions


def _apply_action(state: "SimState", scenario: "Scenario", action: "Action") -> None:
    """Aplica una acción sobre el estado (in-place)."""
    tool_map = {
        "abrir_cerrar_cajas": agent_tools.abrir_cerrar_cajas,
        "reasignar_personal": agent_tools.reasignar_personal,
        "redirigir_aficionados": agent_tools.redirigir_aficionados,
        "activar_recoleccion_rapida": agent_tools.activar_recoleccion_rapida,
    }
    fn = tool_map.get(action.tool)
    if fn is None:
        raise agent_tools.InvalidAction(f"Herramienta desconocida: {action.tool}")
    fn(state, scenario, **action.params)
