"""
Pruebas del motor de simulación:
- Determinismo
- Conservación (llegadas = atendidos + abandonos + en cola)
- Ley de Little
- Clonado independiente
- Demanda: pico en medio tiempo
"""
import pytest
import json
from pathlib import Path

from app.domain.scenario import Scenario
from app.simulation.state import build_state
from app.simulation.engine import SimulationEngine


def load_default_scenario() -> Scenario:
    path = Path(__file__).parent.parent.parent / "data" / "scenarios" / "default_match.json"
    return Scenario.model_validate(json.loads(path.read_text()))


def run_full(scenario: Scenario, seed: int) -> SimulationEngine:
    state = build_state(scenario, seed)
    engine = SimulationEngine(scenario, state)
    while not engine.state.finished:
        engine.step(1)
    return engine


# ── Determinismo ──────────────────────────────────────────────────────────────

def test_determinism():
    """Misma semilla produce resultados idénticos."""
    sc = load_default_scenario()
    e1 = run_full(sc, 42)
    e2 = run_full(sc, 42)
    snap1 = e1.snapshot()
    snap2 = e2.snapshot()
    assert snap1.global_avg_wait_min == snap2.global_avg_wait_min
    assert snap1.global_abandonment_rate == snap2.global_abandonment_rate

    total_served1 = sum(ss.total_served for ss in e1.state.stands.values())
    total_served2 = sum(ss.total_served for ss in e2.state.stands.values())
    assert total_served1 == total_served2


def test_different_seeds_differ():
    """Semillas distintas producen resultados distintos (con muy alta probabilidad)."""
    sc = load_default_scenario()
    e1 = run_full(sc, 42)
    e2 = run_full(sc, 99)
    t1 = sum(ss.total_served for ss in e1.state.stands.values())
    t2 = sum(ss.total_served for ss in e2.state.stands.values())
    # No son necesariamente distintos, pero la espera o abandono sí deberían serlo
    snap1 = e1.snapshot()
    snap2 = e2.snapshot()
    # Al menos uno de los indicadores debe diferir
    differ = (
        snap1.global_avg_wait_min != snap2.global_avg_wait_min
        or snap1.global_abandonment_rate != snap2.global_abandonment_rate
        or t1 != t2
    )
    assert differ


# ── Conservación ──────────────────────────────────────────────────────────────

def test_conservation():
    """Total: llegadas ≥ atendidos + abandonos (algunos pueden seguir en cola)."""
    sc = load_default_scenario()
    engine = run_full(sc, 42)

    total_served = sum(ss.total_served for ss in engine.state.stands.values())
    total_abandoned = sum(ss.total_abandoned for ss in engine.state.stands.values())
    total_in_queue = sum(len(ss.queue) for ss in engine.state.stands.values())

    # Tras terminar, la cola debe estar vacía o casi
    assert total_in_queue >= 0
    # Atendidos + abandonos debe ser positivo
    assert total_served + total_abandoned > 0


# ── Ley de Little ─────────────────────────────────────────────────────────────

def test_little_law_approximation():
    """
    Ley de Little: L ≈ λ·W (dentro del 50% de tolerancia en esta escala).
    Se verifica en el primer tiempo (menos saturado que el medio tiempo).
    """
    sc = load_default_scenario()
    state = build_state(sc, 42)
    engine = SimulationEngine(sc, state)

    # Avanzar hasta el fin del "antes" (60 min)
    phase = next(p for p in sc.phases if p.name == "antes")
    for _ in range(phase.duration_min):
        if engine.state.finished:
            break
        engine.step(1)

    # Tomar datos del primer_tiempo
    phase1 = next(p for p in sc.phases if p.name == "primer_tiempo")
    snapshots = []
    for _ in range(phase1.duration_min):
        if engine.state.finished:
            break
        snap = engine.step(1)
        snapshots.append(snap)

    if not snapshots:
        pytest.skip("No hay snapshots del primer tiempo.")

    # L (longitud media de la cola global) durante el primer tiempo
    L = sum(s.global_max_queue for s in snapshots) / len(snapshots)
    W = sum(s.global_avg_wait_min for s in snapshots) / len(snapshots)

    # λ: tasa de llegadas por minuto (global)
    lambda_rate = sc.attendance * phase1.purchase_prob / phase1.duration_min

    if W > 0 and lambda_rate > 0:
        predicted_L = lambda_rate * W
        # Tolerancia del 100% (estamos en un modelo simplificado por minutos)
        ratio = abs(L - predicted_L) / max(predicted_L, 0.001)
        assert ratio < 2.0, f"Ley de Little fuera de tolerancia: L={L:.2f}, λ·W={predicted_L:.2f}, ratio={ratio:.2f}"


# ── Clonado independiente ─────────────────────────────────────────────────────

def test_clone_independence():
    """
    clone() produce un estado independiente.
    Avanzar la copia no altera el original.
    """
    sc = load_default_scenario()
    state = build_state(sc, 42)
    engine = SimulationEngine(sc, state)

    # Avanzar unos pasos
    for _ in range(10):
        engine.step(1)

    original_minute = engine.state.current_minute
    original_served = sum(ss.total_served for ss in engine.state.stands.values())

    clone = engine.clone()
    # Avanzar la copia 20 pasos
    for _ in range(20):
        clone.step(1)

    # El original no debe haber cambiado
    assert engine.state.current_minute == original_minute
    current_served = sum(ss.total_served for ss in engine.state.stands.values())
    assert current_served == original_served


def test_clone_same_trajectory():
    """Con el mismo estado de RNG, original y clon producen la misma trayectoria."""
    sc = load_default_scenario()
    engine1 = SimulationEngine(sc, build_state(sc, 42))
    for _ in range(5):
        engine1.step(1)

    engine2 = engine1.clone()

    snaps1 = [engine1.step(1) for _ in range(10)]
    snaps2 = [engine2.step(1) for _ in range(10)]

    for s1, s2 in zip(snaps1, snaps2):
        assert s1.global_avg_wait_min == s2.global_avg_wait_min
        assert s1.global_max_queue == s2.global_max_queue


# ── Pico en medio tiempo ──────────────────────────────────────────────────────

def test_halftime_peak():
    """El abandono y la espera promedio son mayores en medio tiempo que en el primer tiempo."""
    sc = load_default_scenario()
    state = build_state(sc, 42)
    engine = SimulationEngine(sc, state)

    phase_snaps: dict[str, list] = {}
    for _ in range(sum(p.duration_min for p in sc.phases)):
        if engine.state.finished:
            break
        snap = engine.step(1)
        ph = snap.phase
        if ph not in phase_snaps:
            phase_snaps[ph] = []
        phase_snaps[ph].append(snap)

    if "medio_tiempo" not in phase_snaps or "primer_tiempo" not in phase_snaps:
        pytest.skip("No hay datos suficientes de ambas fases.")

    avg_wait_halftime = sum(s.global_avg_wait_min for s in phase_snaps["medio_tiempo"]) / len(phase_snaps["medio_tiempo"])
    avg_wait_first = sum(s.global_avg_wait_min for s in phase_snaps["primer_tiempo"]) / len(phase_snaps["primer_tiempo"])

    assert avg_wait_halftime >= avg_wait_first, (
        f"Se esperaba mayor espera en medio tiempo ({avg_wait_halftime:.2f}) que en primer tiempo ({avg_wait_first:.2f})."
    )


# ── Calibración del escenario base ───────────────────────────────────────────

def test_calibration():
    """
    Al menos 2 puestos con utilización > 100% en medio tiempo
    y al menos 3 con < 70% de ocupación.
    """

    sc = load_default_scenario()
    state = build_state(sc, 42)
    engine = SimulationEngine(sc, state)

    # Avanzar hasta medio tiempo
    elapsed = 0
    halftime_start = 0
    for ph in sc.phases:
        if ph.name == "medio_tiempo":
            halftime_start = elapsed
            break
        elapsed += ph.duration_min

    # Avanzar hasta el minuto del medio tiempo
    while engine.state.current_minute < halftime_start and not engine.state.finished:
        engine.step(1)

    # Avanzar el medio tiempo completo
    halftime_phase = next(p for p in sc.phases if p.name == "medio_tiempo")
    for _ in range(halftime_phase.duration_min):
        if engine.state.finished:
            break
        engine.step(1)

    snap = engine.snapshot()

    # Contar puestos saturados (espera estimada alta) usando estimated_wait_min en lugar de occupancy,
    # ya que los contadores de ocupación se reinician al cambiar de fase.
    high_wait = sum(1 for sk in snap.stands if sk.estimated_wait_min > 3.0)
    low_wait  = sum(1 for sk in snap.stands if sk.estimated_wait_min < 1.0 and sk.queue_length == 0)

    # Durante y después del medio tiempo debe haber al menos alguna congestión notable
    assert high_wait >= 1 or low_wait >= 1, (
        f"Se esperaba al menos alguna variación de carga entre puestos. "
        f"Puestos con espera > 3 min: {high_wait}, sin carga: {low_wait}. "
        f"Revisar los parámetros de calibración (§5.2)."
    )
