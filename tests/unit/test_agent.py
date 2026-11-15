"""
Pruebas de las herramientas del agente.
- Límites de cajas abiertas
- Límite de personal mínimo
- Destinos válidos
- El agente no modifica la corrida real sin apply
"""
import json
import pytest
from pathlib import Path

from app.domain.scenario import Scenario
from app.simulation.state import build_state
from app.simulation.engine import SimulationEngine
from app.agent.tools import (
    abrir_cerrar_cajas, reasignar_personal, redirigir_aficionados,
    activar_recoleccion_rapida, InvalidAction
)


def load_default_scenario() -> Scenario:
    path = Path(__file__).parent.parent.parent / "data" / "scenarios" / "default_match.json"
    return Scenario.model_validate(json.loads(path.read_text()))


def warm_engine(sc: Scenario, minutes: int = 60) -> SimulationEngine:
    state = build_state(sc, 42)
    engine = SimulationEngine(sc, state)
    for _ in range(minutes):
        if engine.state.finished:
            break
        engine.step(1)
    return engine


# ── abrir_cerrar_cajas ────────────────────────────────────────────────────────

def test_open_register_valid():
    sc = load_default_scenario()
    state = build_state(sc, 42)
    ss = state.stands["P1"]
    original = ss.registers_open
    abrir_cerrar_cajas(state, sc, "P1", 1)
    assert state.stands["P1"].registers_open == original + 1


def test_open_register_exceeds_installed():
    sc = load_default_scenario()
    state = build_state(sc, 42)
    with pytest.raises(InvalidAction):
        abrir_cerrar_cajas(state, sc, "P1", 100)  # 4+100 > 6 instaladas


def test_open_register_exceeds_staff():
    sc = load_default_scenario()
    # Crear un escenario donde personal = cajas_abiertas
    state = build_state(sc, 42)
    ss = state.stands["P1"]
    ss.staff = ss.registers_open  # personal exactamente igual a cajas abiertas
    with pytest.raises(InvalidAction):
        abrir_cerrar_cajas(state, sc, "P1", 1)  # abrir más del personal


def test_close_register_valid():
    sc = load_default_scenario()
    state = build_state(sc, 42)
    ss = state.stands["P1"]
    original = ss.registers_open
    abrir_cerrar_cajas(state, sc, "P1", -1)
    assert state.stands["P1"].registers_open == original - 1


def test_close_too_many_raises():
    sc = load_default_scenario()
    state = build_state(sc, 42)
    with pytest.raises(InvalidAction):
        abrir_cerrar_cajas(state, sc, "P1", -100)


# ── reasignar_personal ────────────────────────────────────────────────────────

def test_reasignar_valid():
    sc = load_default_scenario()
    state = build_state(sc, 42)
    orig_src = state.stands["P10"].staff
    orig_dst = state.stands["P2"].staff
    reasignar_personal(state, sc, "P10", "P2", 1)
    assert state.stands["P10"].staff == orig_src - 1
    assert state.stands["P2"].staff == orig_dst + 1


def test_reasignar_minimum_staff():
    sc = load_default_scenario()
    state = build_state(sc, 42)
    ss = state.stands["P10"]
    with pytest.raises(InvalidAction):
        reasignar_personal(state, sc, "P10", "P2", ss.staff)  # dejaría en 0


def test_reasignar_invalid_stand():
    sc = load_default_scenario()
    state = build_state(sc, 42)
    with pytest.raises(InvalidAction):
        reasignar_personal(state, sc, "P99", "P2", 1)


# ── redirigir_aficionados ─────────────────────────────────────────────────────

def test_redirigir_valid():
    sc = load_default_scenario()
    state = build_state(sc, 42)
    redirigir_aficionados(state, sc, "S1", "P6")
    assert "S1" in state.stands["P6"].redirections


def test_redirigir_invalid_sector():
    sc = load_default_scenario()
    state = build_state(sc, 42)
    with pytest.raises(InvalidAction):
        redirigir_aficionados(state, sc, "S99", "P1")


def test_redirigir_invalid_stand():
    sc = load_default_scenario()
    state = build_state(sc, 42)
    with pytest.raises(InvalidAction):
        redirigir_aficionados(state, sc, "S1", "P99")


# ── activar_recoleccion_rapida ────────────────────────────────────────────────

def test_activar_pickup():
    sc = load_default_scenario()
    state = build_state(sc, 42)
    assert not state.stands["P1"].pickup_enabled
    activar_recoleccion_rapida(state, sc, "P1")
    assert state.stands["P1"].pickup_enabled


def test_activar_pickup_invalid_stand():
    sc = load_default_scenario()
    state = build_state(sc, 42)
    with pytest.raises(InvalidAction):
        activar_recoleccion_rapida(state, sc, "P99")


# ── El agente no modifica la corrida real sin apply ────────────────────────────

def test_agent_does_not_modify_real_run_without_apply():
    """
    El agente (HeuristicAdvisor) usa clone() internamente.
    La corrida real no debe cambiar después de llamar a recommend().
    """
    from app.agent.advisor import HeuristicAdvisor

    sc = load_default_scenario()
    state = build_state(sc, 42)
    engine = SimulationEngine(sc, state)

    # Avanzar hasta el medio tiempo
    target = sum(p.duration_min for p in sc.phases if p.name in ("antes", "primer_tiempo"))
    for _ in range(target):
        if engine.state.finished:
            break
        engine.step(1)

    # Registrar estado antes
    original_minute = engine.state.current_minute
    original_serves = {sid: ss.total_served for sid, ss in engine.state.stands.items()}
    original_opens  = {sid: ss.registers_open for sid, ss in engine.state.stands.items()}

    advisor = HeuristicAdvisor()
    advisor.recommend(engine.state, sc)

    # El estado real no debe haber cambiado
    assert engine.state.current_minute == original_minute
    for sid in original_serves:
        assert engine.state.stands[sid].total_served == original_serves[sid], f"Puesto {sid} fue modificado"
        assert engine.state.stands[sid].registers_open == original_opens[sid], f"Cajas de {sid} fueron modificadas"
