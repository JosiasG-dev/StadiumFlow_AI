# Guía de Configuración del Agente en IBM watsonx Orchestrate

**StadiumFlow AI — Equipo Geminero · UAT**

---

## Estado actual

> ⚠️ **La prueba contra el servicio IBM real está pendiente por falta de acceso al entorno IBM del curso.**
> Todo el código (`OrchestrateAdvisor`, endpoints de herramientas, especificación OpenAPI) está implementado y listo.
> Solo se requiere configurar las variables de entorno descritas abajo y seguir los pasos de este documento.

---

## 1. Qué está implementado

| Componente | Archivo | Estado |
|---|---|---|
| `OrchestrateAdvisor` | `app/agent/orchestrate_advisor.py` | ✅ Listo |
| Fallback automático a asesor local | `app/agent/orchestrate_advisor.py` | ✅ Listo |
| Endpoints de herramientas (OpenAPI) | `app/api/routes_agent.py` | ✅ Listo |
| Variable `ADVISOR_PROVIDER=orchestrate` | `app/config.py`, `.env.example` | ✅ Listo |
| Especificación OpenAPI generada por FastAPI | `GET /api/openapi.json` | ✅ Listo |

---

## 2. Requisitos previos

- Acceso al entorno IBM del curso (Antigravity / IBM Cloud)
- Una instancia de **IBM watsonx Orchestrate** activa
- API key de la instancia
- ID del agente creado en Orchestrate

---

## 3. Variables de entorno necesarias

Copia `.env.example` a `.env` y configura:

```env
ADVISOR_PROVIDER=orchestrate
ORCHESTRATE_URL=https://<región>.assistant.watson.cloud.ibm.com
ORCHESTRATE_API_KEY=<tu-api-key>
ORCHESTRATE_AGENT_ID=<id-del-agente>
ORCHESTRATE_TIMEOUT=10
```

---

## 4. Pasos para registrar el agente en watsonx Orchestrate

### 4.1 Obtener la especificación OpenAPI de las herramientas

Con la aplicación corriendo:

```
GET http://127.0.0.1:8000/api/openapi.json
```

Los endpoints relevantes son:
- `GET /api/agent/tools` — lista de herramientas
- `POST /api/runs/{run_id}/tools/consultar_filas`
- `POST /api/runs/{run_id}/tools/pronosticar_pico`
- (Las demás herramientas se invocan vía `POST /api/runs/{run_id}/recommendations/{rec_id}/apply`)

### 4.2 Crear el agente en Orchestrate

1. En el panel de watsonx Orchestrate, selecciona **"Create agent"**
2. Nombre: `StadiumFlow Agent`
3. Instrucciones del agente (pegar este bloque):

```
Eres el agente de optimización logística de StadiumFlow AI. Tu función es analizar
el estado de las filas en los puestos de alimentos y bebidas de un estadio durante
un partido de fútbol y recomendar acciones concretas al operador.

Ciclo de trabajo:
1. Llama a consultar_filas para ver el estado actual.
2. Llama a pronosticar_pico para anticipar la demanda.
3. Identifica puestos con espera > 6 minutos (saturados) y puestos sin carga.
4. Propone hasta 3 acciones combinadas: abrir cajas, reasignar personal, redirigir aficionados.
5. Presenta la recomendación en español, con motivo, acción y efecto esperado.
6. Espera la decisión del operador (aprobar, modificar o descartar). Nada se aplica solo.

Restricciones:
- Cajas abiertas ≤ instaladas; cajas abiertas ≤ personal.
- El origen de reasignación conserva al menos 1 empleado.
- Solo recomienda si la mejora estimada es ≥ 10%.
- Los datos son sintéticos; no los presentes como predicciones reales.
```

4. En **Tools**, importa la especificación OpenAPI de `GET /api/openapi.json`
5. Activa los endpoints de herramientas: `consultar_filas`, `pronosticar_pico`
6. Guarda y obtén el **Agent ID**

### 4.3 Configurar la aplicación

```env
ADVISOR_PROVIDER=orchestrate
ORCHESTRATE_URL=<URL de tu instancia>
ORCHESTRATE_API_KEY=<API key>
ORCHESTRATE_AGENT_ID=<Agent ID del paso 4.2>
```

Reinicia la aplicación. El proveedor activo se muestra en `GET /api/agent/status` y en la bitácora de cada corrida.

### 4.4 Verificar el fallback

Deja `ORCHESTRATE_URL` vacío o incorrecto: la aplicación debe seguir funcionando con el asesor local (`HeuristicAdvisor`). El log mostrará:
```
WARNING OrchestrateAdvisor: fallo al llamar al servicio (...). Usando asesor local.
```

---

## 5. Mención de Antigravity

El entorno de desarrollo y ejecución del proyecto es **Antigravity** (entorno virtual IBM del curso). La aplicación corre sobre Python estándar y FastAPI; no requiere instalación adicional en el entorno IBM más allá de las dependencias del `requirements.txt`.

---

## 6. Pasos pendientes para el equipo

Una vez que tengan acceso al entorno IBM:

1. Crear la instancia de Orchestrate en el panel del curso.
2. Seguir el paso 4.2 de este documento.
3. Configurar las variables de entorno.
4. Ejecutar `pytest tests/` para verificar que el fallback funciona.
5. Ejecutar una corrida en modo agente y verificar en la bitácora que el proveedor es `orchestrate`.
6. Documentar el tiempo de respuesta del agente real (indicador del protocolo).
7. Actualizar `docs/informe_de_cierre.md` con los resultados.
