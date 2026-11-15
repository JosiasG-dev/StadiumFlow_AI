"""
Herramientas del agente (funciones puras sobre SimState).
Cada herramienta recibe un SimState y devuelve el nuevo estado modificado.
Se usan en dos contextos:
  a) sobre una copia del estado para probar candidatos (sin efecto en la corrida real)
  b) sobre el estado real de la corrida, solo tras aprobación del usuario
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from app.simulation import kpis as kpi_module

if TYPE_CHECKING:
    from app.domain.scenario import Scenario
    from app.simulation.state import SimState


class InvalidAction(Exception):
    """Acción de herramienta que viola las reglas del dominio."""


def consultar_filas(state: "SimState", scenario: "Scenario") -> list[dict]:
    """
    Devuelve la fila y espera estimada por puesto.
    Herramienta de lectura; no modifica el estado.
    """
    result = []
    for stand_cfg in scenario.stands:
        ss = state.stands[stand_cfg.id]
        est_wait = kpi_module.estimated_wait_min(ss, scenario)
        result.append({
            "stand_id": stand_cfg.id,
            "queue_length": len(ss.queue),
            "estimated_wait_min": round(min(est_wait, 999.0), 2),
            "registers_open": ss.registers_open,
            "staff": ss.staff,
        })
    return result


def pronosticar_pico(state: "SimState", scenario: "Scenario", horizonte_min: int = 10) -> list[dict]:
    """
    Estima las llegadas esperadas por sector en los próximos horizonte_min minutos.
    Herramienta de lectura; no modifica el estado.
    """

    # Fase actual y horizonte por fase
    phases = scenario.phases
    phase_idx = state.phase_index
    phase_min = state.phase_minute

    result = []
    remaining = horizonte_min
    idx = phase_idx
    ph_min = phase_min

    phase_arrivals: dict[str, float] = {s.id: 0.0 for s in scenario.sectors}

    while remaining > 0 and idx < len(phases):
        ph = phases[idx]
        mins_in_this = min(remaining, ph.duration_min - ph_min)
        rate_per_min = scenario.attendance * ph.purchase_prob / ph.duration_min
        for sector in scenario.sectors:
            phase_arrivals[sector.id] += rate_per_min * sector.share * mins_in_this
        remaining -= mins_in_this
        idx += 1
        ph_min = 0

    for sector in scenario.sectors:
        result.append({
            "sector_id": sector.id,
            "expected_arrivals": round(phase_arrivals[sector.id], 1),
            "horizon_min": horizonte_min,
        })
    return result


def abrir_cerrar_cajas(state: "SimState", scenario: "Scenario", stand_id: str, delta: int) -> "SimState":
    """
    Abre (delta > 0) o cierra (delta < 0) cajas en un puesto.
    Reglas: cajas_abiertas ∈ [0, instaladas] y cajas_abiertas ≤ personal.
    """
    if stand_id not in state.stands:
        raise InvalidAction(f"Puesto '{stand_id}' no existe.")
    stand_cfg = next((s for s in scenario.stands if s.id == stand_id), None)
    if stand_cfg is None:
        raise InvalidAction(f"Configuración del puesto '{stand_id}' no encontrada.")

    ss = state.stands[stand_id]
    new_open = ss.registers_open + delta

    if new_open < 0:
        raise InvalidAction(f"No se pueden cerrar más cajas de las que están abiertas en {stand_id}.")
    if new_open > stand_cfg.registers_installed:
        raise InvalidAction(
            f"Puesto {stand_id}: cajas solicitadas ({new_open}) superan las instaladas ({stand_cfg.registers_installed})."
        )
    if new_open > ss.staff:
        raise InvalidAction(
            f"Puesto {stand_id}: cajas solicitadas ({new_open}) superan el personal disponible ({ss.staff})."
        )

    ss.registers_open = new_open
    return state


def reasignar_personal(
    state: "SimState", scenario: "Scenario", origen_id: str, destino_id: str, cantidad: int
) -> "SimState":
    """
    Mueve `cantidad` empleados del puesto origen al destino.
    El origen conserva al menos 1 empleado.
    """
    if origen_id not in state.stands:
        raise InvalidAction(f"Puesto origen '{origen_id}' no existe.")
    if destino_id not in state.stands:
        raise InvalidAction(f"Puesto destino '{destino_id}' no existe.")
    if cantidad <= 0:
        raise InvalidAction("La cantidad de personal a mover debe ser mayor que cero.")

    ss_origen = state.stands[origen_id]
    ss_destino = state.stands[destino_id]

    if ss_origen.staff - cantidad < 1:
        raise InvalidAction(
            f"El puesto origen {origen_id} no puede quedar sin personal. "
            f"Personal actual: {ss_origen.staff}, solicitado mover: {cantidad}."
        )

    ss_origen.staff -= cantidad
    # Ajustar cajas abiertas si ahora superan al personal
    ss_origen.registers_open = min(ss_origen.registers_open, ss_origen.staff)

    ss_destino.staff += cantidad
    return state


def redirigir_aficionados(
    state: "SimState", scenario: "Scenario", sector_id: str, stand_destino_id: str
) -> "SimState":
    """
    Activa la redirección de un sector hacia un puesto específico.
    La fracción redirect_compliance del escenario rige la obediencia.
    """
    if not any(s.id == sector_id for s in scenario.sectors):
        raise InvalidAction(f"Sector '{sector_id}' no existe.")
    if not any(s.id == stand_destino_id for s in scenario.stands):
        raise InvalidAction(f"Puesto destino '{stand_destino_id}' no existe.")

    # Registrar la redirección en el estado del puesto destino
    ss_destino = state.stands[stand_destino_id]
    ss_destino.redirections[sector_id] = stand_destino_id
    return state


def activar_recoleccion_rapida(state: "SimState", scenario: "Scenario", stand_id: str) -> "SimState":
    """
    Habilita la ventana de recolección rápida para pedido móvil en un puesto.
    """
    if stand_id not in state.stands:
        raise InvalidAction(f"Puesto '{stand_id}' no existe.")
    state.stands[stand_id].pickup_enabled = True
    return state
