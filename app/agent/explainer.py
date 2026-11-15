"""
Generación de explicaciones en lenguaje natural para las recomendaciones del agente.
Texto en español sin tecnicismos, generado por plantillas.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.scenario import Scenario
    from app.simulation.state import SimState
    from app.domain.recommendation import Action, ExpectedEffect

# Mapeo de herramientas a frases de resumen
_TOOL_SUMMARY: dict[str, str] = {
    "abrir_cerrar_cajas": "ajustar cajas abiertas en {stand_id}",
    "reasignar_personal": "mover {cantidad} empleado(s) de {origen_id} a {destino_id}",
    "redirigir_aficionados": "redirigir el sector {sector_id} hacia {stand_destino_id}",
    "activar_recoleccion_rapida": "activar recolección rápida en {stand_id}",
}

_TOOL_MOTIVE: dict[str, str] = {
    "abrir_cerrar_cajas": "{stand_id} presenta fila larga; abrir más cajas reduce la espera.",
    "reasignar_personal": "{destino_id} necesita refuerzo; {origen_id} opera con baja demanda.",
    "redirigir_aficionados": "El sector {sector_id} está dirigiendo mucho flujo a un puesto congestionado.",
    "activar_recoleccion_rapida": "Una parte importante de los aficionados usa pedido móvil en {stand_id}; la ventana de recolección agiliza su atención.",
}


def _format_action_summary(action: "Action") -> str:
    template = _TOOL_SUMMARY.get(action.tool, action.tool)
    try:
        return template.format(**action.params)
    except KeyError:
        return f"{action.tool}({action.params})"


def _format_action_motive(action: "Action") -> str:
    template = _TOOL_MOTIVE.get(action.tool, "")
    if not template:
        return ""
    try:
        return template.format(**action.params)
    except KeyError:
        return ""


def build_recommendation_text(
    actions: list["Action"],
    state: "SimState",
    scenario: "Scenario",
    expected_effect: "ExpectedEffect | None",
) -> tuple[str, str]:
    """
    Devuelve (motive, summary) para una lista de acciones.
    """
    # Motivo: combinar los motivos únicos de cada acción
    motives = []
    for action in actions:
        m = _format_action_motive(action)
        if m and m not in motives:
            motives.append(m)
    motive = " ".join(motives) if motives else "Se detectó congestión en uno o más puestos."

    # Resumen: lista de acciones en lenguaje natural
    summaries = [_format_action_summary(a) for a in actions]
    if len(summaries) == 1:
        summary = summaries[0].capitalize() + "."
    elif len(summaries) == 2:
        summary = f"{summaries[0].capitalize()} y {summaries[1]}."
    else:
        summary = ", ".join(s.capitalize() for s in summaries[:-1]) + f" y {summaries[-1]}."

    # Añadir el efecto esperado si está disponible
    if expected_effect is not None:
        wait_delta = expected_effect.avg_wait_before_min - expected_effect.avg_wait_after_min
        abd_delta = expected_effect.abandonment_before_pct - expected_effect.abandonment_after_pct
        if wait_delta > 0:
            summary += (
                f" Se espera reducir la espera promedio de "
                f"{expected_effect.avg_wait_before_min:.1f} a "
                f"{expected_effect.avg_wait_after_min:.1f} min en los próximos "
                f"{expected_effect.horizon_min} minutos."
            )
        if abd_delta > 0:
            summary += (
                f" El abandono estimado bajaría del "
                f"{expected_effect.abandonment_before_pct:.0f}% al "
                f"{expected_effect.abandonment_after_pct:.0f}%."
            )

    return motive, summary
