"""
Pruebas de integración de la API HTTP.
Flujo completo: crear escenario → corrida base → corrida agente → aplicar → comparar → exportar.
"""
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def default_scenario_payload():
    path = Path(__file__).parent.parent.parent / "data" / "scenarios" / "default_match.json"
    return json.loads(path.read_text())


# ── Escenarios ────────────────────────────────────────────────────────────────

def test_list_scenarios():
    res = client.get("/api/scenarios")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_create_and_get_scenario():
    payload = default_scenario_payload()
    payload["id"] = "test-api-sc"
    payload["name"] = "Escenario de prueba API"

    # Crear
    res = client.post("/api/scenarios", json=payload)
    assert res.status_code in (201, 409), res.text

    # Obtener
    res = client.get("/api/scenarios/test-api-sc")
    assert res.status_code == 200
    assert res.json()["id"] == "test-api-sc"


def test_create_scenario_invalid_id():
    payload = default_scenario_payload()
    payload["id"] = "INVALID ID!"
    res = client.post("/api/scenarios", json=payload)
    assert res.status_code == 422


def test_scenario_not_found():
    res = client.get("/api/scenarios/does-not-exist-xyz")
    assert res.status_code == 404
    assert "error" in res.json()


def test_duplicate_scenario():
    # Asegurar que existe el default
    _ = client.get("/api/scenarios/default_match")
    if _.status_code == 404:
        pytest.skip("default_match no existe en el repositorio de prueba.")

    res = client.post("/api/scenarios/default_match/duplicate", json={
        "new_id": "dup-test-scenario",
        "new_name": "Copia de prueba",
    })
    assert res.status_code in (201, 409)


# ── Corridas base ─────────────────────────────────────────────────────────────

def test_create_base_run():
    # Asegurar que el escenario por defecto existe
    sc_res = client.get("/api/scenarios/default_match")
    if sc_res.status_code == 404:
        pytest.skip("default_match no está en el repositorio de prueba.")

    res = client.post("/api/runs", json={"scenario_id": "default_match", "mode": "base"})
    assert res.status_code == 201
    assert "run_id" in res.json()
    return res.json()["run_id"]


def test_step_and_state():
    sc_res = client.get("/api/scenarios/default_match")
    if sc_res.status_code == 404:
        pytest.skip("default_match no disponible.")

    run_id = client.post("/api/runs", json={"scenario_id": "default_match", "mode": "base"}).json()["run_id"]

    # Avanzar 1 minuto
    res = client.post(f"/api/runs/{run_id}/step", json={"minutes": 1})
    assert res.status_code == 200
    data = res.json()
    assert "snapshot" in data
    assert data["snapshot"]["minute"] >= 0

    # Estado
    res = client.get(f"/api/runs/{run_id}/state")
    assert res.status_code == 200


def test_run_to_end_base():
    sc_res = client.get("/api/scenarios/default_match")
    if sc_res.status_code == 404:
        pytest.skip("default_match no disponible.")

    run_id = client.post("/api/runs", json={"scenario_id": "default_match", "mode": "base"}).json()["run_id"]
    res = client.post(f"/api/runs/{run_id}/run-to-end", json={})
    assert res.status_code == 200
    assert res.json()["finished"] is True

    # Intentar avanzar una corrida terminada → 409
    res2 = client.post(f"/api/runs/{run_id}/step", json={"minutes": 1})
    assert res2.status_code == 409


# ── Corrida agente ────────────────────────────────────────────────────────────

def test_agent_run_recommendations():
    sc_res = client.get("/api/scenarios/default_match")
    if sc_res.status_code == 404:
        pytest.skip("default_match no disponible.")

    run_id = client.post("/api/runs", json={"scenario_id": "default_match", "mode": "agent"}).json()["run_id"]

    # Avanzar hasta que haya al menos una recomendación o se termine
    max_steps = 100
    for _ in range(max_steps):
        res = client.post(f"/api/runs/{run_id}/step", json={"minutes": 1})
        data = res.json()
        if data.get("finished"):
            break
        if data.get("all_pending"):
            rec_id = data["all_pending"][0]["id"]
            # Aplicar la primera recomendación
            apply_res = client.post(f"/api/runs/{run_id}/recommendations/{rec_id}/apply", json={})
            assert apply_res.status_code == 200
            break

    # Verificar bitácora
    audit_res = client.get(f"/api/runs/{run_id}/audit")
    assert audit_res.status_code == 200


# ── Comparación ───────────────────────────────────────────────────────────────

def test_comparison():
    sc_res = client.get("/api/scenarios/default_match")
    if sc_res.status_code == 404:
        pytest.skip("default_match no disponible.")

    res = client.post("/api/comparisons", json={
        "scenario_id": "default_match",
        "replicas": 2,
        "seed": 42,
    })
    assert res.status_code == 201
    data = res.json()
    assert "id" in data
    comp_id = data["id"]

    # Obtener comparación
    res2 = client.get(f"/api/comparisons/{comp_id}")
    assert res2.status_code == 200

    # Exportar CSV
    res_csv = client.get(f"/api/comparisons/{comp_id}/export?format=csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers.get("content-type", "")

    # Exportar JSON
    res_json = client.get(f"/api/comparisons/{comp_id}/export?format=json")
    assert res_json.status_code == 200


# ── Validaciones ──────────────────────────────────────────────────────────────

def test_replicas_exceeds_max():
    res = client.post("/api/comparisons", json={
        "scenario_id": "default_match",
        "replicas": 9999,
    })
    assert res.status_code == 422


def test_run_not_found():
    res = client.get("/api/runs/does-not-exist/state")
    assert res.status_code == 404
