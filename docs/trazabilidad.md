# Trazabilidad — StadiumFlow AI

Verificación de cumplimiento respecto al protocolo del proyecto.  
**Equipo:** Geminero · UAT – Facultad de Ingeniería Tampico

---

## Tabla de trazabilidad protocolo → evidencia

| Elemento del protocolo | Debe existir como | Evidencia en el proyecto | Estado |
|---|---|---|---|
| **Objetivo general** | Aplicación que simula y optimiza el flujo con agente, reduce esperas/congestión | `app/` completo; corrida base + agente + comparación | ✅ |
| **Objetivo 1** | Documento de requerimientos con historias de usuario priorizadas | `docs/requerimientos.md` | ✅ |
| **Objetivo 2** | Modelo del recinto y archivo de parámetros configurable | `data/scenarios/*.json`; formulario en `/scenarios/new` | ✅ |
| **Objetivo 3** | Simulación ejecutable con indicadores por puesto y etapa | `app/simulation/`; `GET /api/runs/{id}/state` | ✅ |
| **Objetivo 4** | Agente con ≥ 4 herramientas (se implementan 6) y recomendaciones registradas | `app/agent/`; `GET /api/runs/{id}/recommendations` | ✅ |
| **Objetivo 5** | Panel navegable validado con lista de tareas | `app/templates/simulation.html`; `docs/validacion_usuarios.md` | ✅ |
| **Objetivo 6** | Informe comparativo base vs. agente en distintas configuraciones | `POST /api/comparisons`; pantalla Informes | ✅ |
| **F1 — Configurar escenario** | CRUD + formulario completo + 3 precargados | `/scenarios`, `/api/scenarios` | ✅ |
| **F2 — Simular demanda** | Motor por pasos de 1 min, 5 etapas, pico en medio tiempo | `app/simulation/engine.py`, `demand.py` | ✅ |
| **F3 — Calcular indicadores** | Espera, fila, abandono, ocupación, densidad, ingreso | `app/simulation/kpis.py` | ✅ |
| **F4 — Panel de control** | 4 KPI, mapa de calor, recomendaciones, línea de tiempo, Ajustes | `/simulation/{run_id}`, `/settings` | ✅ |
| **F5 — Agente IA** | 6 herramientas, prueba antes de recomendar, Orchestrate | `app/agent/`, `app/agent/orchestrate_advisor.py` | ✅ |
| **F6 — Control humano** | Aprobar/modificar/descartar; bitácora con tiempo de respuesta | `POST /api/runs/{id}/recommendations/{rid}/apply` | ✅ |
| **F7 — Comparación** | Réplicas, semilla común, media ± desviación, distintas configs | `POST /api/comparisons` | ✅ |
| **F8 — Exportación** | CSV, JSON, PDF con advertencia de datos sintéticos | `GET /api/comparisons/{id}/export?format=pdf\|csv\|json` | ✅ |
| **§6.5 Usabilidad** | Lenguaje claro, señales visuales, recomendaciones accionables, control del usuario, informes comprensibles | Verificado en plantillas HTML y CSS | ✅ |
| **§8 Componente innovador** | Repartir flujo · agente que prueba antes · explicaciones · comparación · anticipación · accesibilidad | `planner.py`, `explainer.py`, `anticipation_share` | ✅ |
| **§9.2 Limitaciones** | Declaradas en la aplicación y la documentación | Aviso en informe PDF; `docs/informe_de_cierre.md` | ✅ |
| **§11.1 Productos esperados** | Prototipo funcional, requerimientos, diseño, informe, presentación | `docs/` completo | ✅ |
| **Pantalla de Ajustes** | Implementada (antes marcada fuera de alcance en el MVP) | `/settings` | ✅ |
| **OrchestrateAdvisor** | Implementado; prueba contra IBM pendiente por falta de acceso | `app/agent/orchestrate_advisor.py`; `docs/guia_watsonx_orchestrate.md` | ⏳ Pendiente prueba real |
| **Validación con personas** | Instrumentos listos; aplicación pendiente | `docs/validacion_usuarios.md` | ⏳ Pendiente aplicación |

---

## Funciones F1–F8: endpoints y pruebas

| Función | Endpoint principal | Prueba automática |
|---|---|---|
| F1 | `POST /api/scenarios` | `test_create_and_get_scenario` |
| F2 | Motor interno (`engine.step`) | `test_determinism`, `test_halftime_peak` |
| F3 | `GET /api/runs/{id}/state` | `test_step_and_state` |
| F4 | `GET /simulation/{run_id}` (HTML) | Manual (navegador) |
| F5 | `POST /api/runs/{id}/step` (modo agent) | `test_agent_run_recommendations` |
| F6 | `POST /api/runs/{id}/recommendations/{rid}/apply` | `test_agent_does_not_modify_real_run_without_apply` |
| F7 | `POST /api/comparisons` | `test_comparison` |
| F8 | `GET /api/comparisons/{id}/export` | `test_comparison` (verifica CSV y JSON) |

---

## Desviaciones respecto al protocolo

| Elemento | Decisión tomada | Justificación |
|---|---|---|
| Pantalla de Ajustes | Implementada (el protocolo la mencionaba en boceto pero no en las 4 áreas) | El documento de completado la exige explícitamente |
| PDF exportado como HTML imprimible | Se usa la función de impresión del navegador | No hay dependencia de PDF permitida; el resultado es equivalente |
| Coordenadas de puestos en formulario | Fijas en el JS; editables solo vía JSON | Mantiene la simplicidad del formulario sin perder configurabilidad |
| Validación con personas reales | Instrumentos listos; aplicación pendiente | No es posible realizarla en el entorno de código; requiere acceso al equipo |
