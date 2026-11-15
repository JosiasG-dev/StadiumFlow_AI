# StadiumFlow AI — MVP v0.1

Simulador de logística de zonas de alimentos y bebidas de un estadio, con un **agente de IA** que analiza el estado de la simulación, prueba acciones candidatas y recomienda decisiones explicadas al operador.

> **Datos sintéticos.** Los resultados son ilustrativos, no predicciones reales.

---

## Instalación y ejecución en 5 comandos

```bash
# 1. Crear entorno virtual
python -m venv .venv && .venv/Scripts/activate   # Windows
# python -m venv .venv && source .venv/bin/activate  # Linux/macOS

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Copiar configuración
copy .env.example .env   # Windows
# cp .env.example .env   # Linux/macOS

# 4. Iniciar la aplicación
uvicorn app.main:app --reload

# 5. Abrir en el navegador
# http://127.0.0.1:8000
```

La documentación interactiva de la API está en `http://127.0.0.1:8000/api/docs`.

### Pruebas

```bash
pip install -r requirements-dev.txt
pytest
```

---

## Flujo de uso

```
Inicio → Escenarios (crear/editar) → Simulación (corrida base) →
Agente IA (corrida con agente + aprobación) → Informes (comparar + exportar)
```

---

## Arquitectura

```
app/
├── api/          ← Endpoints FastAPI (solo habla con services/)
├── web/          ← Rutas HTML con Jinja2
├── domain/       ← Modelos Pydantic y validaciones de negocio
├── simulation/   ← Motor de simulación (no depende de api/ ni agent/)
├── agent/        ← Herramientas, planificador, explicador, bitácora
├── services/     ← Casos de uso (ScenarioService, RunService, etc.)
├── repositories/ ← Interfaces (Protocol) e implementación JSON
└── templates/    ← Plantillas Jinja2
```

**Reglas de dependencia:**
- `simulation/` no importa nada de `api/`, `services/`, `agent/` ni FastAPI.
- `agent/` solo importa `simulation/` y `domain/`.
- `api/` solo habla con `services/`; nunca con repositorios directamente.

---

## Variables de entorno (`.env`)

| Variable | Por defecto | Descripción |
|---|---|---|
| `APP_ENV` | `development` | Entorno |
| `HOST` / `PORT` | `127.0.0.1` / `8000` | Enlace local |
| `DATA_DIR` | `./data` | Carpeta de persistencia JSON |
| `DEFAULT_SEED` | `42` | Semilla base de aleatoriedad |
| `DEFAULT_REPLICAS` | `10` | Réplicas para comparar escenarios |
| `MAX_REPLICAS` | `30` | Tope de seguridad |
| `ADVISOR_PROVIDER` | `heuristic` | `heuristic` (MVP) · `orchestrate` (v2) |

---

## Supuestos documentados

1. **Aforo 2 500**: representa solo a los aficionados atendidos por los 10 puestos, para que puedan saturarse de forma plausible.
2. **Parámetros numéricos** (cajas, personal, tiempos de servicio, paciencia, ticket): sintéticos y editables por JSON. El protocolo original solo fija 10 puestos, 5 fases, 3 perfiles y el pico en medio tiempo.
3. **Resolución de 1 minuto**: coherente con el ejemplo "cada minuto" del protocolo.
4. **`redirect_compliance = 0.60`**: fracción de aficionados que sigue una redirección; no definida en el PDF del protocolo.
5. **Función de puntuación del agente**: `score = espera_total + 8 × abandonos`. El coeficiente 8 es una estimación documentada en `config.py`.
6. **Umbral de mejora del 10 %**: el agente solo recomienda si la mejora proyectada supera este umbral.
7. **Sin pantalla de Ajustes**: aparece en el boceto del protocolo pero no en las cuatro áreas de navegación descritas; se omite en el MVP.
8. **Meta del ≥20 % de reducción en medio tiempo**: hipótesis del protocolo, no resultado garantizado.

---

## Agente de IA — estado actual

> ⚠️ **IMPLEMENTACIÓN PROVISIONAL**: el agente (`HeuristicAdvisor`) es un módulo local determinista basado en búsqueda anticipada y reglas heurísticas. **No usa LLM ni IBM watsonx Orchestrate.**
> 
> La interfaz `Advisor` está diseñada para que en v2 se pueda conectar un `OrchestrateAdvisor` sin modificar el motor ni la API.

### Herramientas del agente (6 funciones)

| Herramienta | Tipo | Descripción |
|---|---|---|
| `consultar_filas` | Lectura | Devuelve fila y espera estimada por puesto |
| `pronosticar_pico` | Lectura | Llegadas esperadas por sector en el horizonte |
| `abrir_cerrar_cajas` | Acción | Cambia cajas abiertas (≤ instaladas y ≤ personal) |
| `reasignar_personal` | Acción | Mueve personal entre puestos (origen ≥ 1) |
| `redirigir_aficionados` | Acción | Activa redirección de un sector hacia un puesto |
| `activar_recoleccion_rapida` | Acción | Habilita ventana de recolección para pedido móvil |

---

## Fuera del alcance del MVP

Conexión con punto de venta, cámaras o sensores · app móvil · simulación de evacuación o seguridad · pagos reales · predicción con datos históricos reales · autenticación y multiusuario · exportación PDF · integración real con watsonx Orchestrate · pantalla de Ajustes.

---

## Notas de operación

- El MVP **requiere un solo proceso** de Uvicorn (`uvicorn app.main:app` sin `--workers`). Las corridas activas viven en memoria; con varios procesos se perderían.
- Los archivos JSON se escriben atómicamente (archivo temporal + renombrado) para minimizar la corrupción en caso de fallo.
- La semilla de aleatoriedad garantiza reproducibilidad: comparaciones base/agente con la misma semilla producen las mismas condiciones de demanda.

---

## Proyecto — contexto académico

UAT — Facultad de Ingeniería Tampico · Equipo Geminero · Proyecto Integrador (Unidad 1)
