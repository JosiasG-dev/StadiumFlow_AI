"""
Repositorios basados en archivos JSON.
Escritura atómica: se escribe en archivo temporal y luego se renombra,
evitando archivos corruptos en caso de fallo.
"""
import json
import logging
import os
import tempfile
from pathlib import Path

from app.domain.scenario import Scenario
from app.domain.results import RunResult, ComparisonResult

logger = logging.getLogger(__name__)

# Límite de tamaño de JSON leído (10 MB) para evitar archivos maliciosos
MAX_JSON_SIZE = 10 * 1024 * 1024


def _safe_path(base_dir: Path, filename: str) -> Path:
    """
    Construye una ruta segura dentro de base_dir.
    Lanza ValueError si la ruta resuelta escapa del directorio base.
    """
    resolved = (base_dir / filename).resolve()
    if not str(resolved).startswith(str(base_dir.resolve())):
        raise ValueError(f"Ruta no permitida: {filename}")
    return resolved


def _atomic_write(path: Path, data: str) -> None:
    """Escribe atomicamente: archivo temporal + renombrado."""
    dir_path = path.parent
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=str(dir_path),
        delete=False,
        suffix=".tmp",
    ) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    os.replace(tmp_path, str(path))


class JsonScenarioRepository:
    def __init__(self, data_dir: Path) -> None:
        self._dir = data_dir / "scenarios"
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, scenario_id: str) -> Path:
        return _safe_path(self._dir, f"{scenario_id}.json")

    def get(self, scenario_id: str) -> Scenario | None:
        path = self._path(scenario_id)
        if not path.exists():
            return None
        if path.stat().st_size > MAX_JSON_SIZE:
            logger.warning("Archivo de escenario demasiado grande: %s", path)
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return Scenario.model_validate(data)

    def list_all(self) -> list[Scenario]:
        scenarios: list[Scenario] = []
        for f in sorted(self._dir.glob("*.json")):
            if f.stat().st_size > MAX_JSON_SIZE:
                continue
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                scenarios.append(Scenario.model_validate(data))
            except Exception as exc:
                logger.warning("No se pudo cargar el escenario %s: %s", f.name, exc)
        return scenarios

    def save(self, scenario: Scenario) -> None:
        path = self._path(scenario.id)
        _atomic_write(path, scenario.model_dump_json(indent=2))

    def delete(self, scenario_id: str) -> None:
        path = self._path(scenario_id)
        if path.exists():
            path.unlink()


class JsonRunRepository:
    def __init__(self, data_dir: Path) -> None:
        self._runs_dir = data_dir / "runs"
        self._comparisons_dir = data_dir / "runs"
        self._runs_dir.mkdir(parents=True, exist_ok=True)

    def save_result(self, result: RunResult) -> None:
        path = _safe_path(self._runs_dir, f"{result.run_id}.json")
        _atomic_write(path, result.model_dump_json(indent=2))

    def get_result(self, run_id: str) -> RunResult | None:
        path = _safe_path(self._runs_dir, f"{run_id}.json")
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return RunResult.model_validate(data)

    def save_comparison(self, result: ComparisonResult) -> None:
        path = _safe_path(self._runs_dir, f"comparison_{result.id}.json")
        _atomic_write(path, result.model_dump_json(indent=2))

    def get_comparison(self, comparison_id: str) -> ComparisonResult | None:
        path = _safe_path(self._runs_dir, f"comparison_{comparison_id}.json")
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return ComparisonResult.model_validate(data)


class JsonAuditRepository:
    def __init__(self, data_dir: Path) -> None:
        self._dir = data_dir / "audit"
        self._dir.mkdir(parents=True, exist_ok=True)

    def append(self, run_id: str, record: dict) -> None:
        path = _safe_path(self._dir, f"{run_id}.jsonl")
        line = json.dumps(record, ensure_ascii=False) + "\n"
        with open(str(path), "a", encoding="utf-8") as f:
            f.write(line)

    def read(self, run_id: str) -> list[dict]:
        path = _safe_path(self._dir, f"{run_id}.jsonl")
        if not path.exists():
            return []
        records: list[dict] = []
        with open(str(path), encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return records
