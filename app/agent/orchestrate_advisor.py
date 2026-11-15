"""
OrchestrateAdvisor — integración con IBM watsonx Orchestrate.
Implementa el mismo contrato de Advisor que HeuristicAdvisor.
Fallback automático al asesor local si el servicio no responde.

CONFIGURACIÓN:
  ADVISOR_PROVIDER=orchestrate
  ORCHESTRATE_URL=https://<región>.assistant.watson.cloud.ibm.com/...
  ORCHESTRATE_API_KEY=<api-key>
  ORCHESTRATE_TIMEOUT=10          # segundos de espera máxima
  ORCHESTRATE_AGENT_ID=<agent-id>

ESTADO DE PRUEBA CONTRA IBM:
  Pendiente por falta de acceso al entorno IBM del curso.
  Todo el código está listo; solo se requiere configurar las variables de entorno.
  Ver docs/guia_watsonx_orchestrate.md para los pasos de configuración.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import TYPE_CHECKING

from app.agent.advisor import HeuristicAdvisor

if TYPE_CHECKING:
    from app.domain.scenario import Scenario
    from app.simulation.state import SimState
    from app.domain.recommendation import Recommendation

logger = logging.getLogger(__name__)


class OrchestrateAdvisor:
    """
    Asesor que delega en IBM watsonx Orchestrate.
    Fallback automático a HeuristicAdvisor si el servicio no está disponible.
    """

    def __init__(
        self,
        url: str,
        api_key: str,
        agent_id: str,
        timeout: int = 10,
    ) -> None:
        self._url = url.rstrip("/")
        self._api_key = api_key
        self._agent_id = agent_id
        self._timeout = timeout
        self._fallback = HeuristicAdvisor()

    def recommend(self, state: "SimState", scenario: "Scenario") -> list["Recommendation"]:
        """
        Envía el estado al agente de Orchestrate y convierte la respuesta
        en Recommendation. Si falla, usa el asesor local.
        """
        try:
            return self._call_orchestrate(state, scenario)
        except Exception as exc:
            logger.warning(
                "OrchestrateAdvisor: fallo al llamar al servicio (%s). Usando asesor local.",
                exc,
            )
            recs = self._fallback.recommend(state, scenario)
            # Marcar que vienen del asesor de respaldo
            for rec in recs:
                rec.motive = f"[Respaldo local] {rec.motive}"
            return recs

    def _call_orchestrate(
        self, state: "SimState", scenario: "Scenario"
    ) -> list["Recommendation"]:
        from app.simulation import kpis as kmod
        from app.domain.recommendation import Recommendation, Action

        snap = kmod.snapshot(state, scenario)

        # Construir el mensaje de contexto para el agente
        context = {
            "minute": state.current_minute,
            "phase": scenario.phases[min(state.phase_index, len(scenario.phases) - 1)].name,
            "stands": [
                {
                    "id": sk.stand_id,
                    "queue": sk.queue_length,
                    "estimated_wait_min": sk.estimated_wait_min,
                    "registers_open": sk.registers_open,
                    "staff": sk.staff,
                }
                for sk in snap.stands
            ],
            "global_avg_wait_min": snap.global_avg_wait_min,
            "global_abandonment_rate": snap.global_abandonment_rate,
        }

        body = json.dumps({
            "agent_id": self._agent_id,
            "input": {
                "text": "Analiza el estado actual y proporciona recomendaciones de optimización.",
                "context": context,
            },
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self._url}/v2/assistants/{self._agent_id}/sessions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        # Parsear la respuesta — Orchestrate devuelve las herramientas invocadas
        # como tool_calls. Las convertimos a nuestro formato Action.
        actions = []
        response_text = ""
        output = data.get("output", {})
        for tool_call in output.get("tool_calls", []):
            fn = tool_call.get("function", {})
            try:
                params = json.loads(fn.get("arguments", "{}"))
            except json.JSONDecodeError:
                params = {}
            actions.append(Action(tool=fn.get("name", "unknown"), params=params))
        response_text = output.get("generic", [{}])[0].get("text", "Sin respuesta del agente.")

        if not actions:
            return []

        from app.agent.explainer import build_recommendation_text
        motive, summary = build_recommendation_text(actions, state, scenario, None)
        if response_text:
            summary = response_text


        rec_id = f"orc-{state.current_minute:04d}"
        rec = Recommendation(
            id=rec_id,
            run_id=state.scenario_id,
            minute=state.current_minute,
            status="pending",
            motive=motive,
            actions=actions,
            summary=summary,
        )
        return [rec]
