"""
Rutas del agente: estado, herramientas OpenAPI y conversación.
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_run_service
from app.services.run_service import RunService

router = APIRouter()
RunServiceDep = Annotated[RunService, Depends(get_run_service)]


@router.get("/agent/status")
def agent_status() -> dict:
    """Estado del proveedor de agente configurado."""
    from app.config import get_settings
    settings = get_settings()
    return {
        "provider": settings.advisor_provider,
        "orchestrate_configured": bool(settings.orchestrate_url and settings.orchestrate_api_key),
        "note": "Agente local de reglas y simulación; compatible con migración a IBM watsonx Orchestrate.",
    }


# ── Herramientas del agente expuestas como API (para Orchestrate) ──────────

@router.get("/agent/tools")
def list_tools() -> list[dict]:
    """Lista las herramientas del agente con su descripción (para importar en Orchestrate)."""
    return [
        {"name": "consultar_filas",          "description": "Devuelve la longitud de fila y espera estimada de cada puesto.", "read_only": True},
        {"name": "pronosticar_pico",          "description": "Estima las llegadas esperadas en el horizonte de minutos indicado.", "read_only": True},
        {"name": "abrir_cerrar_cajas",        "description": "Abre o cierra cajas en un puesto. Parámetros: stand_id, delta (positivo=abrir, negativo=cerrar).", "read_only": False},
        {"name": "reasignar_personal",        "description": "Mueve personal de un puesto a otro. Parámetros: origen_id, destino_id, cantidad.", "read_only": False},
        {"name": "redirigir_aficionados",     "description": "Activa redirección de un sector hacia un puesto. Parámetros: sector_id, stand_destino_id.", "read_only": False},
        {"name": "activar_recoleccion_rapida","description": "Activa ventana de recolección rápida en un puesto. Parámetros: stand_id.", "read_only": False},
    ]


@router.post("/runs/{run_id}/tools/consultar_filas")
def tool_consultar_filas(run_id: str, svc: RunServiceDep) -> list[dict]:
    """Herramienta: estado actual de filas y espera estimada."""
    from app.services.run_service import _registry
    entry = _registry.get(run_id)
    if entry is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Corrida no encontrada.")
    from app.agent.tools import consultar_filas
    return consultar_filas(entry.engine.state, entry.scenario)


@router.post("/runs/{run_id}/tools/pronosticar_pico")
def tool_pronosticar_pico(run_id: str, horizonte_min: int = 10, svc: RunServiceDep = None) -> list[dict]:
    """Herramienta: pronóstico de llegadas en el horizonte indicado."""
    from app.services.run_service import _registry
    entry = _registry.get(run_id)
    if entry is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Corrida no encontrada.")
    from app.agent.tools import pronosticar_pico
    return pronosticar_pico(entry.engine.state, entry.scenario, horizonte_min)


# ── Conversación con el agente ─────────────────────────────────────────────

class ChatMessage(BaseModel):
    message: str


@router.post("/runs/{run_id}/chat")
def agent_chat(run_id: str, body: ChatMessage, svc: RunServiceDep) -> dict:
    """
    Responde preguntas del operador sobre el estado de la corrida.
    Usa plantillas con datos reales; no inventa cifras.
    """
    from app.services.run_service import _registry
    entry = _registry.get(run_id)
    if entry is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Corrida no encontrada.")

    state = entry.engine.state
    scenario = entry.scenario
    recs = entry.recommendations

    from app.simulation import kpis as kmod
    snap = kmod.snapshot(state, scenario)

    response = _answer_question(body.message, snap, recs, state, scenario)
    return {"response": response, "minute": state.current_minute}


def _answer_question(question: str, snap, recs, state, scenario) -> str:
    """Genera una respuesta basada en el estado real de la corrida."""
    q = question.lower().strip()

    # Buscar el puesto más saturado
    saturated = sorted(snap.stands, key=lambda s: s.estimated_wait_min, reverse=True)
    top = saturated[0] if saturated else None

    # Respuestas por intención detectada
    if any(w in q for w in ["fila", "espera", "cola", "tiempo"]):
        lines = [f"**Estado actual de filas (min. {snap.minute}, etapa: {snap.phase}):**"]
        for sk in snap.stands:
            wait = sk.estimated_wait_min if sk.estimated_wait_min < 999 else "—"
            lines.append(f"• {sk.stand_id}: {sk.queue_length} personas, espera est. {wait} min")
        return "\n".join(lines)

    if any(w in q for w in ["saturado", "congestion", "problema", "peor", "mayor"]):
        if top:
            return (
                f"El puesto más cargado ahora es **{top.stand_id}** con {top.queue_length} personas "
                f"en fila y espera estimada de {top.estimated_wait_min:.1f} min. "
                f"Tiene {top.registers_open} cajas abiertas y {top.staff} empleados."
            )
        return "No hay puestos con congestión en este momento."

    if any(w in q for w in ["recomiend", "acción", "hacer", "sugerir", "propone"]):
        pending = [r for r in recs if r.status == "pending"]
        if pending:
            r = pending[0]
            return f"Recomendación pendiente (min. {r.minute}): {r.summary}"
        applied = [r for r in recs if r.status == "applied"]
        if applied:
            last = applied[-1]
            return f"La última acción aplicada fue en el min. {last.minute}: {last.summary}"
        return "El agente no ha emitido recomendaciones hasta ahora."

    if any(w in q for w in ["abandono", "se van", "se fueron", "sin comprar"]):
        return (
            f"Tasa de abandono global actual: {snap.global_abandonment_rate*100:.1f}%. "
            f"Espera promedio: {snap.global_avg_wait_min:.1f} min."
        )

    if any(w in q for w in ["etapa", "fase", "minuto", "tiempo simulado"]):
        phase_idx = min(state.phase_index, len(scenario.phases) - 1)
        phase = scenario.phases[phase_idx]
        mins_left = phase.duration_min - state.phase_minute
        return (
            f"Estamos en la etapa **{snap.phase}** (min. {snap.minute}). "
            f"Quedan aproximadamente {mins_left} minutos en esta etapa."
        )

    if any(w in q for w in ["no aplico", "descart", "qué pasa si no"]):
        pending = [r for r in recs if r.status == "pending"]
        if pending and pending[0].expected_effect:
            eff = pending[0].expected_effect
            return (
                f"Si no se aplica la recomendación pendiente, se estima que la espera promedio "
                f"se mantendrá en {eff.avg_wait_before_min:.1f} min durante los próximos "
                f"{eff.horizon_min} minutos, frente a {eff.avg_wait_after_min:.1f} min si se aplica."
            )
        return "No hay una recomendación pendiente con efecto estimado en este momento."

    # Respuesta genérica de estado
    return (
        f"Estado al min. {snap.minute} (etapa: {snap.phase}): "
        f"espera promedio {snap.global_avg_wait_min:.1f} min, "
        f"abandono {snap.global_abandonment_rate*100:.1f}%, "
        f"ocupación {snap.global_occupancy*100:.1f}%. "
        f"Puedes preguntar sobre filas, saturación, recomendaciones, abandono o etapa actual."
    )
