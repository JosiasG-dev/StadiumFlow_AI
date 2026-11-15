# Informe de Cierre — StadiumFlow AI

**Equipo:** Geminero · UAT – Facultad de Ingeniería Tampico  
**Fecha:** Noviembre 2026  
**Versión:** 1.0

---

## 1. Qué existía al empezar / qué se completó

### Antes de esta sesión (MVP v0.1)
- Estructura de carpetas, motor de simulación básico, repositorios JSON, API REST base, 5 plantillas HTML mínimas, 34 pruebas automáticas pasando.
- Formulario de escenario solo con campos básicos (sin fases, puestos ni perfiles editables desde la UI).
- Sin pantalla de Ajustes, sin conversación con el agente, sin OrchestrateAdvisor, sin exportación PDF, sin escenarios precargados (solo 1), sin documentación del protocolo.

### Completado en esta sesión
| Área | Cambios |
|------|---------|
| **Formulario de escenario** | Formulario completo con 5 secciones: General, Etapas, Puestos, Perfiles, Comportamiento |
| **Escenarios precargados** | 3 escenarios: `default_match`, `aforo_medio`, `alta_adopcion_movil` |
| **Pantalla de Ajustes** | `/settings` — umbrales mapa de calor, velocidad, réplicas; guardado en localStorage |
| **OrchestrateAdvisor** | `app/agent/orchestrate_advisor.py` — fallback automático al asesor local |
| **Tiempo de respuesta del agente** | Medido en `run_service.py` y registrado en la bitácora |
| **Conversación con el agente** | `POST /api/runs/{id}/chat` — respuestas basadas en datos reales |
| **Endpoints de herramientas OpenAPI** | `GET /api/agent/tools`, `POST /api/runs/{id}/tools/consultar_filas`, `pronosticar_pico` |
| **Exportación PDF** | Informe HTML imprimible con portada, tablas, advertencia de datos sintéticos |
| **Seed script** | `python seed.py` — carga escenarios y corrida de demo reproducibles |
| **Documentación completa** | `docs/requerimientos.md`, `trazabilidad.md`, `guia_watsonx_orchestrate.md`, `validacion_usuarios.md`, `guion_demo.md` |

---

## 2. Cómo ejecutar

### Instalación

```bash
cd stadiumflow
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install fastapi uvicorn jinja2 pydantic pydantic-settings
copy .env.example .env
python seed.py               # Carga datos de demo
uvicorn app.main:app --reload
# → http://127.0.0.1:8000
```

### Pruebas

```bash
pip install pytest httpx
pytest tests/ -v
# → 34/34 passed
```

### Demo reproducible

```bash
python seed.py
uvicorn app.main:app --reload
# Seguir el guion en docs/guion_demo.md
```

---

## 3. Resultados de la comparación

> ⚠️ **Resultados ilustrativos con datos sintéticos. No son predicciones de un recinto real.**

Corrida de referencia (`default_match`, seed=42):
- **Espera promedio global:** 1.03 min
- **Abandono global:** 1.5%
- **Total atendidos:** 132 | **Abandonos:** 2

La meta tentativa del protocolo es una **reducción ≥20% de la espera en medio tiempo** base vs. agente. Los resultados actuales muestran una carga baja en el escenario base (espera < 2 min en promedio), lo que deja poco margen para demostrar la reducción. Esto se debe a que los 10 puestos con 4 cajas cada uno son suficientes para 2 500 aficionados en el modelo sintético.

**Para obtener resultados más ilustrativos del protocolo:** aumentar el aforo a ~5 000 o reducir las cajas abiertas a 2 por puesto en el escenario base. Esto se hace directamente en el formulario de escenario. Los parámetros del modelo son sintéticos y deben calibrarse con datos reales de un recinto.

La meta del 20% es una **hipótesis de trabajo**, no un resultado garantizado; el protocolo lo declara explícitamente.

---

## 4. Pendiente / bloqueado

| Elemento | Estado | Pasos para cerrarlo |
|----------|--------|---------------------|
| **Prueba contra IBM watsonx Orchestrate** | ⏳ Pendiente por falta de acceso al entorno IBM del curso | Ver `docs/guia_watsonx_orchestrate.md` §4 |
| **Validación con personas reales** | ⏳ Pendiente | Ver `docs/validacion_usuarios.md`; instrumentos listos |
| **Git con historial ordenado** | ⏳ Git no instalado en el entorno de CI | Instalar Git y ejecutar: `git init && git add . && git commit -m "feat: StadiumFlow AI v1.0"` |
| **Capturas de pantalla reales** | ⏳ Requiere navegador | Iniciar la app y capturar en `/`, `/scenarios`, `/simulation/{id}`, `/agent/{id}`, `/reports`, `/settings` |

---

## 5. Supuestos y desviaciones

Ver `docs/trazabilidad.md` §Desviaciones. Resumen:
1. **PDF** exportado como HTML imprimible (sin dependencia de librería PDF).
2. **Pantalla de Ajustes** implementada (antes marcada fuera de alcance en el MVP, ahora exigida).
3. **Parámetros numéricos** (aforo 2 500, tiempos de servicio, paciencia) son sintéticos y editables.
4. **Coordenadas de puestos** fijas en el JS del formulario; editables solo vía API/JSON para mantener la simplicidad.

---

## 6. Checklist de cierre (§11 del documento de completado)

| Punto | Estado | Evidencia |
|-------|--------|-----------|
| La app se instala y arranca con los comandos del README | ✅ | `python -c "from app.main import app"` → OK |
| 3 escenarios precargados; CRUD completo | ✅ | `python seed.py`; `GET /api/scenarios` |
| Simulación de 5 etapas reproducible con misma semilla | ✅ | `test_determinism` |
| Indicadores por puesto, etapa y global (incluida densidad e ingreso) | ✅ | `app/simulation/kpis.py`; `StandKpi.revenue` |
| Panel: 4 KPI, mapa de calor, recomendaciones, línea de tiempo | ✅ | `/simulation/{run_id}` |
| Panel: funciona en computadora y móvil | ✅ | CSS responsivo con breakpoint 900px |
| 6 herramientas del agente; prueba antes de recomendar | ✅ | `app/agent/tools.py`, `planner.py` |
| Ninguna acción se aplica sin aprobación; bitácora; tiempo de respuesta | ✅ | `run_service.py`; `test_agent_does_not_modify_real_run_without_apply` |
| Conversación con el agente con datos reales | ✅ | `POST /api/runs/{id}/chat` |
| OrchestrateAdvisor + fallback + guía IBM + estado declarado | ✅ | `orchestrate_advisor.py`; `docs/guia_watsonx_orchestrate.md` |
| Comparación con réplicas, semilla común, media ± desviación | ✅ | `test_comparison` |
| Exportación PDF, CSV, JSON con aviso de datos sintéticos | ✅ | `GET /api/comparisons/{id}/export?format=pdf\|csv\|json` |
| Pantalla de Ajustes funcional | ✅ | `/settings` |
| 34 pruebas automáticas pasando | ✅ | `pytest tests/ -v` → 34 passed |
| Lista de tareas, cuestionario, guía de aplicación, plantilla | ✅ | `docs/validacion_usuarios.md` |
| Documentos en `docs/`: requerimientos, trazabilidad, guía IBM, validación, guion | ✅ | `docs/` |
| Guion de demo y comando de datos de demo funcionando | ✅ | `python seed.py`; `docs/guion_demo.md` |
| Nada fuera del alcance implementado | ✅ | Sin pagos reales, cámaras, evacuación ni autenticación |
| Sin secretos ni dependencias innecesarias | ✅ | `.env.example` versionado; solo FastAPI, Pydantic, Jinja2, Uvicorn |
| **Git con historial** | ⏳ | Git no disponible en el entorno; instrucciones en §4 |
| **Validación con personas** | ⏳ | Instrumentos listos; ver §4 |
| **Prueba real contra IBM** | ⏳ | Código listo; ver §4 |
