"""
seed.py — Carga los escenarios de demostración y ejecuta una corrida de ejemplo.
Ejecutar desde la carpeta stadiumflow/:
    python seed.py

Resultado: escenarios precargados en data/scenarios/ y una corrida base del
escenario default_match persistida en data/runs/ para demostración.
"""
import json
import sys
from pathlib import Path

# Asegurar que el módulo app está en el path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import get_settings
from app.repositories.json_repository import JsonScenarioRepository, JsonRunRepository, JsonAuditRepository
from app.domain.scenario import Scenario
from app.simulation.engine import SimulationEngine
from app.simulation.state import build_state
from app.domain.results import RunResult, PhaseResult

SCENARIO_IDS = ["default_match", "aforo_medio", "alta_adopcion_movil"]


def main() -> None:
    settings = get_settings()
    data_dir = settings.data_dir
    scenarios_dir = data_dir / "scenarios"
    scenarios_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "runs").mkdir(parents=True, exist_ok=True)
    (data_dir / "audit").mkdir(parents=True, exist_ok=True)

    repo = JsonScenarioRepository(data_dir)

    print("── Cargando escenarios de demostración ──")
    seed_dir = Path(__file__).parent / "data" / "scenarios"
    loaded = 0
    for sc_id in SCENARIO_IDS:
        path = seed_dir / f"{sc_id}.json"
        if not path.exists():
            print(f"  ⚠️  Archivo no encontrado: {path}")
            continue
        sc = Scenario.model_validate(json.loads(path.read_text()))
        existing = repo.get(sc_id)
        if existing is None:
            repo.save(sc)
            print(f"  ✅ Escenario cargado: {sc.name} ({sc_id})")
            loaded += 1
        else:
            print(f"  ✓  Ya existe: {sc_id}")

    print(f"\n── Ejecutando corrida de demostración (default_match, semilla 42) ──")
    sc = repo.get("default_match")
    if sc is None:
        print("  ⚠️  Escenario default_match no encontrado. Abortando corrida de demo.")
        return

    state = build_state(sc, 42)
    engine = SimulationEngine(sc, state)
    while not engine.state.finished:
        engine.step(1)

    # Persistir resultado
    run_repo = JsonRunRepository(data_dir)
    total_served = sum(ss.total_served for ss in state.stands.values())
    total_abandoned = sum(ss.total_abandoned for ss in state.stands.values())
    total_wait = sum(ss.total_wait_min for ss in state.stands.values())
    global_avg = total_wait / max(total_served, 1)
    global_abd = total_abandoned / max(total_served + total_abandoned, 1)

    result = RunResult(
        run_id="demo-default-seed42",
        scenario_id="default_match",
        mode="base",
        seed=42,
        total_minutes=state.current_minute,
        global_avg_wait_min=round(global_avg, 2),
        global_abandonment_rate=round(global_abd, 4),
        total_served=total_served,
        total_abandoned=total_abandoned,
    )
    run_repo.save_result(result)

    print(f"  ✅ Corrida demo guardada: demo-default-seed42")
    print(f"     Total atendidos: {total_served} | Abandonos: {total_abandoned}")
    print(f"     Espera promedio: {global_avg:.2f} min | Abandono: {global_abd*100:.1f}%")
    print(f"\n── Listo. Inicia la app con: uvicorn app.main:app --reload ──")


if __name__ == "__main__":
    main()
