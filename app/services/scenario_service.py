"""
ScenarioService — casos de uso para la gestión de escenarios.
"""
from __future__ import annotations


from app.domain.scenario import Scenario
from app.repositories.base import ScenarioRepository


class ScenarioNotFound(Exception):
    pass


class ScenarioAlreadyExists(Exception):
    pass


class ScenarioService:
    def __init__(self, repo: ScenarioRepository) -> None:
        self._repo = repo

    def list_scenarios(self) -> list[Scenario]:
        return self._repo.list_all()

    def get_scenario(self, scenario_id: str) -> Scenario:
        sc = self._repo.get(scenario_id)
        if sc is None:
            raise ScenarioNotFound(f"Escenario '{scenario_id}' no encontrado.")
        return sc

    def create_scenario(self, scenario: Scenario) -> Scenario:
        existing = self._repo.get(scenario.id)
        if existing is not None:
            raise ScenarioAlreadyExists(f"Ya existe un escenario con id '{scenario.id}'.")
        self._repo.save(scenario)
        return scenario

    def update_scenario(self, scenario_id: str, scenario: Scenario) -> Scenario:
        existing = self._repo.get(scenario_id)
        if existing is None:
            raise ScenarioNotFound(f"Escenario '{scenario_id}' no encontrado.")
        # El id del body debe coincidir con el de la ruta
        updated = scenario.model_copy(update={"id": scenario_id})
        self._repo.save(updated)
        return updated

    def delete_scenario(self, scenario_id: str) -> None:
        existing = self._repo.get(scenario_id)
        if existing is None:
            raise ScenarioNotFound(f"Escenario '{scenario_id}' no encontrado.")
        self._repo.delete(scenario_id)

    def duplicate_scenario(self, scenario_id: str, new_id: str, new_name: str) -> Scenario:
        original = self._repo.get(scenario_id)
        if original is None:
            raise ScenarioNotFound(f"Escenario '{scenario_id}' no encontrado.")
        existing = self._repo.get(new_id)
        if existing is not None:
            raise ScenarioAlreadyExists(f"Ya existe un escenario con id '{new_id}'.")
        duplicate = original.model_copy(update={"id": new_id, "name": new_name})
        self._repo.save(duplicate)
        return duplicate
