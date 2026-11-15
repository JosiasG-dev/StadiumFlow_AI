"""
ReportService — exportación de comparaciones a CSV, JSON y PDF (HTML imprimible).
"""
from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Literal

from app.domain.results import ComparisonResult
from app.repositories.base import RunRepository


ExportFormat = Literal["csv", "json", "pdf"]


class ReportService:
    def __init__(self, run_repo: RunRepository) -> None:
        self._run_repo = run_repo

    def export(self, comparison_id: str, fmt: ExportFormat) -> tuple[str, str]:
        """
        Devuelve (contenido, media_type) para la comparación indicada.
        """
        result = self._run_repo.get_comparison(comparison_id)
        if result is None:
            from app.services.scenario_service import ScenarioNotFound
            raise ScenarioNotFound(f"Comparación '{comparison_id}' no encontrada.")

        if fmt == "json":
            return result.model_dump_json(indent=2), "application/json"
        elif fmt == "pdf":
            return self._to_html_report(result), "text/html"
        else:
            return self._to_csv(result), "text/csv"

    def _to_csv(self, result: ComparisonResult) -> str:
        output = io.StringIO()
        writer = csv.writer(output)

        # Encabezado global
        writer.writerow(["escenario_id", "replicas", "reduccion_espera_pct", "reduccion_abandono_pct"])
        writer.writerow([
            result.scenario_id,
            result.replicas,
            result.global_avg_wait_reduction_pct,
            result.global_abandonment_reduction_pct,
        ])
        writer.writerow([])

        # Por fase
        writer.writerow(["fase", "espera_media_base", "espera_std_base", "abandono_medio_base",
                         "abandono_std_base", "reduccion_espera_medio_tiempo_pct"])
        for pa in result.phase_aggregates:
            writer.writerow([
                pa.phase,
                pa.avg_wait_mean,
                pa.avg_wait_std,
                pa.abandonment_mean,
                pa.abandonment_std,
                pa.halftime_wait_reduction_pct if pa.halftime_wait_reduction_pct is not None else "",
            ])
        writer.writerow([])

        # Por réplica
        writer.writerow(["semilla", "modo", "espera_global", "abandono_global"])
        for replica in result.replica_results:
            writer.writerow([replica.seed, "base", replica.base.global_avg_wait_min, replica.base.global_abandonment_rate])
            writer.writerow([replica.seed, "agente", replica.agent.global_avg_wait_min, replica.agent.global_abandonment_rate])

        return output.getvalue()

    def _to_html_report(self, result: ComparisonResult) -> str:
        """Genera un informe HTML imprimible (exportable a PDF con Ctrl+P del navegador)."""
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        rows_phase = ""
        for pa in result.phase_aggregates:
            red = f"{pa.halftime_wait_reduction_pct:.1f}%" if pa.halftime_wait_reduction_pct is not None else "—"
            rows_phase += (
                f"<tr><td>{pa.phase}</td>"
                f"<td>{pa.avg_wait_mean:.2f} ± {pa.avg_wait_std:.2f}</td>"
                f"<td>{pa.abandonment_mean*100:.1f}% ± {pa.abandonment_std*100:.1f}%</td>"
                f"<td>{red}</td></tr>"
            )

        rows_replica = ""
        for r in result.replica_results[:10]:  # máximo 10 en el PDF
            rows_replica += (
                f"<tr><td>{r.seed}</td>"
                f"<td>{r.base.global_avg_wait_min:.2f}</td>"
                f"<td>{r.base.global_abandonment_rate*100:.1f}%</td>"
                f"<td>{r.agent.global_avg_wait_min:.2f}</td>"
                f"<td>{r.agent.global_abandonment_rate*100:.1f}%</td></tr>"
            )

        return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Informe Comparativo — StadiumFlow AI</title>
  <style>
    @page {{ margin: 2cm; }}
    body {{ font-family: 'Segoe UI', sans-serif; font-size: 12pt; color: #1f2328; line-height: 1.5; }}
    h1 {{ color: #1F3A5F; font-size: 20pt; margin-bottom: .2em; }}
    h2 {{ color: #1F3A5F; font-size: 14pt; border-bottom: 2px solid #e5e7eb; padding-bottom: .3em; margin-top: 1.5em; }}
    .subtitle {{ color: #57606a; font-size: 11pt; margin-bottom: 2em; }}
    .warning {{ background: #fef9c3; border: 1px solid #fde68a; padding: .6em 1em; border-radius: 4px; font-size: 10pt; margin-bottom: 1.5em; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 10pt; margin-bottom: 1em; }}
    th {{ background: #1F3A5F; color: #fff; padding: .4em .7em; text-align: left; }}
    td {{ padding: .35em .7em; border-bottom: 1px solid #e5e7eb; }}
    tr:nth-child(even) {{ background: #f7f8fa; }}
    .kpi-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 1em; margin-bottom: 1.5em; }}
    .kpi-box {{ background: #f7f8fa; border: 1px solid #e5e7eb; border-radius: 4px; padding: .8em 1.2em; }}
    .kpi-label {{ font-size: 9pt; color: #57606a; }}
    .kpi-value {{ font-size: 18pt; font-weight: 700; color: #1F3A5F; }}
    .footer {{ margin-top: 3em; font-size: 9pt; color: #57606a; border-top: 1px solid #e5e7eb; padding-top: .8em; }}
    @media print {{ .no-print {{ display: none; }} }}
  </style>
</head>
<body>

<div class="no-print" style="background:#1F3A5F;color:#fff;padding:.8em 1.5em;margin-bottom:1.5em;display:flex;justify-content:space-between;align-items:center;">
  <span><strong>StadiumFlow AI</strong> — Vista previa del informe</span>
  <button onclick="window.print()" style="background:#fff;color:#1F3A5F;border:none;padding:.4em 1em;border-radius:4px;cursor:pointer;font-weight:600;">Imprimir / Guardar PDF</button>
</div>

<h1>Informe Comparativo de Simulación</h1>
<div class="subtitle">StadiumFlow AI · Equipo Geminero · UAT – Facultad de Ingeniería Tampico<br>
  Generado el {now} · Escenario: <strong>{result.scenario_id}</strong> · {result.replicas} réplicas
</div>

<div class="warning">
  ⚠️ <strong>Resultados ilustrativos basados en datos sintéticos. No son predicciones de un recinto real.</strong>
  La meta tentativa de ≥20% de reducción en medio tiempo es una hipótesis de trabajo del protocolo.
</div>

<h2>Resumen global</h2>
<div class="kpi-grid">
  <div class="kpi-box">
    <div class="kpi-label">Reducción de espera promedio</div>
    <div class="kpi-value">{result.global_avg_wait_reduction_pct:.1f}%</div>
  </div>
  <div class="kpi-box">
    <div class="kpi-label">Reducción de abandono</div>
    <div class="kpi-value">{result.global_abandonment_reduction_pct:.1f}%</div>
  </div>
  <div class="kpi-box">
    <div class="kpi-label">Réplicas ejecutadas</div>
    <div class="kpi-value">{result.replicas}</div>
  </div>
  <div class="kpi-box">
    <div class="kpi-label">Semillas utilizadas</div>
    <div class="kpi-value" style="font-size:12pt">{', '.join(str(s) for s in result.seeds[:5])}{'…' if len(result.seeds) > 5 else ''}</div>
  </div>
</div>

<h2>Resultados por etapa</h2>
<table>
  <thead>
    <tr>
      <th>Etapa</th>
      <th>Espera promedio base (media ± desv.)</th>
      <th>Abandono base (media ± desv.)</th>
      <th>Reducción espera medio tiempo</th>
    </tr>
  </thead>
  <tbody>{rows_phase}</tbody>
</table>

<h2>Resultados por réplica (primeras 10)</h2>
<table>
  <thead>
    <tr>
      <th>Semilla</th>
      <th>Espera base (min)</th>
      <th>Abandono base</th>
      <th>Espera agente (min)</th>
      <th>Abandono agente</th>
    </tr>
  </thead>
  <tbody>{rows_replica}</tbody>
</table>

<h2>Metodología</h2>
<p>Comparación automática: para cada semilla se ejecuta una corrida <em>base</em> (sin intervención)
y una corrida <em>agente</em> (aprobación automática). Las condiciones de demanda son idénticas para
ambas gracias a la semilla compartida. Se reporta la media y desviación estándar muestral (N-1).</p>
<p>El agente utiliza búsqueda anticipada con un horizonte de 10 minutos simulados y un umbral mínimo
de mejora del 10% para emitir una recomendación. Herramientas disponibles: 6.</p>

<h2>Limitaciones</h2>
<ul>
  <li>Los parámetros (aforo, tiempos de servicio, perfiles) son sintéticos y no provienen de un recinto real.</li>
  <li>El modelo no incluye evacuación, accesos, estacionamiento ni seguridad física.</li>
  <li>La comparación usa aprobación automática del agente; los resultados interactivos pueden diferir.</li>
  <li>El agente local (HeuristicAdvisor) es una implementación provisional sin LLM.</li>
</ul>

<div class="footer">
  StadiumFlow AI v0.1 · Datos sintéticos · Generado el {now}<br>
  Este informe es un producto académico del Equipo Geminero, UAT – Facultad de Ingeniería Tampico.
  No debe utilizarse para decisiones operativas reales.
</div>

</body>
</html>"""
