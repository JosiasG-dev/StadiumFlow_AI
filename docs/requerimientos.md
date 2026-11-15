# Documento de Requerimientos — StadiumFlow AI

**Proyecto:** StadiumFlow AI — Simulador de logística con agente de IA para zonas de alimentos y bebidas  
**Equipo:** Geminero · UAT – Facultad de Ingeniería Tampico  
**Versión:** 1.0

---

## 1. Problemática y contexto

Los estadios de fútbol concentran miles de aficionados en sus zonas de alimentos y bebidas durante el medio tiempo, generando colas largas, abandono de fila y pérdidas de ingreso. El personal operativo no dispone de herramientas de apoyo en tiempo real para redistribuir cajas y personal de forma preventiva.

---

## 2. Requerimientos funcionales

| ID | Función | Descripción |
|----|---------|-------------|
| RF-01 | F1 | CRUD completo de escenarios: crear, leer, editar, duplicar y eliminar desde UI y API |
| RF-02 | F1 | Formulario con secciones: General, Etapas, Puestos, Perfiles, Comportamiento |
| RF-03 | F1 | Tres escenarios precargados: partido estándar, aforo medio, alta adopción móvil |
| RF-04 | F2 | Motor de simulación de eventos discretos por pasos de 1 minuto, semilla controlada |
| RF-05 | F2 | Cinco etapas del evento con intensidad variable; pico en medio tiempo |
| RF-06 | F3 | Cálculo de indicadores por puesto, por etapa y global: espera, fila, abandono, ocupación, densidad, ingreso |
| RF-07 | F3 | Palanca de anticipación de demanda (opcional) |
| RF-08 | F4 | Panel con 4 KPI, mapa de calor SVG, recomendaciones con botones, línea de tiempo de etapas |
| RF-09 | F4 | Controles: iniciar, pausar, +1 min, +5 min, velocidad, reiniciar, terminar |
| RF-10 | F4 | Pantalla de Ajustes (umbrales mapa de calor, velocidad, réplicas) |
| RF-11 | F5 | Agente con 6 herramientas; prueba candidatos en simulador antes de recomendar |
| RF-12 | F5 | Recomendación con motivo, acción y efecto esperado en español |
| RF-13 | F6 | El usuario aprueba, modifica o descarta cada recomendación; nada se aplica solo |
| RF-14 | F6 | Bitácora auditable: minuto, decisión, KPI antes y después, tiempo de respuesta del agente, proveedor |
| RF-15 | F6 | Conversación con el agente en lenguaje natural, basada en datos reales de la corrida |
| RF-16 | F7 | Comparación base vs. agente con N réplicas y semilla común; media y desviación estándar |
| RF-17 | F7 | Gráficas por etapa y reducción porcentual de espera en medio tiempo |
| RF-18 | F8 | Exportación a CSV, JSON y PDF (imprimible con advertencia de datos sintéticos) |
| RF-19 | — | Integración con IBM watsonx Orchestrate: OrchestrateAdvisor + fallback local |

---

## 3. Requerimientos no funcionales

| ID | Categoría | Descripción |
|----|-----------|-------------|
| RNF-01 | Usabilidad | Legible en segundos; lenguaje sin tecnicismos; mapa de calor con color + número |
| RNF-02 | Usabilidad | Responsivo para computadora y móvil (breakpoint 900 px) |
| RNF-03 | Accesibilidad | Contraste suficiente; estados no dependientes solo del color; foco visible; aria-label |
| RNF-04 | Seguridad | Validación Pydantic en toda entrada; path traversal imposible; sin secretos en repo |
| RNF-05 | Reproducibilidad | Misma semilla → mismos resultados; comparación base/agente con semilla compartida |
| RNF-06 | Calidad | Código limpio; pruebas automáticas en verde; ruff sin advertencias |
| RNF-07 | Trazabilidad | Proveedor del agente registrado en cada corrida |

---

## 4. Historias de usuario priorizadas

### HU-01 — Configurar el escenario (Must)
**Como** operador de logística,  
**quiero** configurar el recinto (puestos, personal, perfiles de aficionado y etapas del evento)  
**para** reflejar las condiciones reales del partido antes de simular.  
**Criterios de aceptación:**
- Formulario con validaciones; errores en español
- Archivo JSON editable por escenario
- Tres escenarios precargados disponibles al instalar

### HU-02 — Ejecutar simulación base (Must)
**Como** operador,  
**quiero** correr la simulación sin intervención del agente  
**para** ver qué ocurre si no se hace nada durante el evento.  
**Criterios de aceptación:**
- Corrida completa de las 5 etapas
- KPIs actualizados en cada paso
- Mapa de calor que refleja la congestión en medio tiempo

### HU-03 — Recibir recomendaciones del agente (Must)
**Como** operador,  
**quiero** que el agente me sugiera acciones concretas con su justificación  
**para** decidir si las aplico o no.  
**Criterios de aceptación:**
- Recomendación con motivo, acción y efecto esperado
- Botones Aplicar / Descartar visibles
- Nada se aplica sin mi decisión

### HU-04 — Comparar escenarios (Must)
**Como** supervisor,  
**quiero** ver la diferencia entre la corrida base y la corrida con agente en varias réplicas  
**para** evaluar el potencial del agente.  
**Criterios de aceptación:**
- Media ± desviación estándar por indicador y etapa
- Reducción porcentual en medio tiempo con advertencia de hipótesis
- Exportación a CSV, JSON y PDF

### HU-05 — Preguntar al agente (Should)
**Como** operador durante el evento,  
**quiero** hacer preguntas al agente en lenguaje natural  
**para** entender qué está pasando sin revisar tablas.  
**Criterios de aceptación:**
- Respuesta basada en datos reales de la corrida
- No inventa cifras

### HU-06 — Ajustar preferencias (Should)
**Como** operador,  
**quiero** cambiar los umbrales del mapa de calor y la velocidad de simulación  
**para** adaptar la herramienta a mis preferencias.

---

## 5. Trazabilidad requerimientos → funciones → objetivos

| Requerimiento | Función | Objetivo específico |
|---------------|---------|---------------------|
| RF-01 a RF-03 | F1 | OE-2 |
| RF-04 a RF-07 | F2, F3 | OE-2, OE-3 |
| RF-08 a RF-10 | F4 | OE-5 |
| RF-11 a RF-15 | F5, F6 | OE-4 |
| RF-16 a RF-17 | F7 | OE-6 |
| RF-18 | F8 | OE-6 |
| RF-19 | F5 | OE-4 |
