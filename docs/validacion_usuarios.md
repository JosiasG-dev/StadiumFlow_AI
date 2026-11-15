# Validación con Usuarios — StadiumFlow AI

---

## Perfil del usuario principal

| Atributo | Descripción |
|---|---|
| **Rol** | Operador de logística de zona de alimentos y bebidas en estadio |
| **Experiencia tecnológica** | Básica-media (usa tablet/smartphone, no requiere conocimientos de simulación) |
| **Contexto de uso** | Panel de control durante el medio tiempo del partido (máximo 15 minutos disponibles) |
| **Necesidad principal** | Saber en segundos cuál puesto está colapsado y qué hacer |
| **Criterio de éxito** | Puede usar el sistema sin capacitación previa, con solo la guía de inicio rápido |

---

## Lista de tareas de usuario

| # | Tarea | Tiempo máximo | Criterio de éxito |
|---|-------|--------------|-------------------|
| T1 | Crear un nuevo escenario con nombre y aforo distintos a los predeterminados | 5 min | Escenario aparece en la lista |
| T2 | Iniciar la simulación base del escenario predeterminado y pausarla en el minuto 60 | 2 min | KPIs visibles y mapa de calor con colores |
| T3 | Identificar el puesto con mayor espera en el mapa de calor | 30 seg | Respuesta correcta |
| T4 | Avanzar hasta el medio tiempo y esperar a que el agente proponga una recomendación | 3 min | Recomendación visible con motivo y efecto esperado |
| T5 | Aplicar la recomendación del agente | 30 seg | Botón "Aplicar" funciona; estado cambia a "applied" |
| T6 | Descartar una segunda recomendación | 30 seg | Estado cambia a "discarded" |
| T7 | Ir a Informes, seleccionar el escenario y ejecutar una comparación con 5 réplicas | 3 min | Tabla de resultados visible |
| T8 | Descargar el informe en CSV | 30 seg | Archivo descargado y abierto correctamente |
| T9 | Cambiar el umbral del mapa de calor en Ajustes | 1 min | Preferencia guardada |
| T10 | Preguntar al agente "¿cuál es el puesto más saturado?" | 1 min | Respuesta con datos reales |

**Umbral de aceptación:** 80% de las tareas completadas con éxito en el tiempo indicado.

---

## Cuestionario breve (escala Likert 1–5)

| # | Pregunta | Escala |
|---|----------|--------|
| Q1 | ¿Qué tan fácil fue entender el mapa de calor? | 1 (muy difícil) – 5 (muy fácil) |
| Q2 | ¿Las recomendaciones del agente son claras y fáciles de entender? | 1 – 5 |
| Q3 | ¿Confiarías en las recomendaciones del agente para tomar decisiones reales? | 1 – 5 |
| Q4 | ¿La información en pantalla es suficiente para actuar durante el medio tiempo? | 1 – 5 |
| Q5 | ¿Los informes son comprensibles para alguien que no participó en la simulación? | 1 – 5 |
| Q6 | ¿Recomendarías esta herramienta a otros operadores de estadio? | 1 – 5 |
| Q7 | (Abierta) ¿Qué cambiarías o agregarías? | Texto libre |
| Q8 | (Para personal con experiencia en recinto) ¿Los parámetros del modelo reflejan la operación real? | 1 – 5 + comentario |

**Umbral de aceptación:** Promedio ≥ 3.5 en Q1–Q6.

---

## Guía de aplicación

1. Pedir a la persona participante que lea el guion de tareas sin ver la aplicación.
2. Entregarle la URL de la aplicación en un dispositivo limpio.
3. Registrar el tiempo de cada tarea y si se completó (sí/no).
4. Al terminar, pedir que llene el cuestionario.
5. Registrar los resultados en `validacion_resultados.csv`.

---

## Plantilla de registro (validacion_resultados.csv)

```csv
participante_id,perfil,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,q1,q2,q3,q4,q5,q6,comentario
P01,operador,si,si,si,si,si,no,si,si,si,si,4,4,3,5,4,4,"Muy útil pero el mapa es pequeño en móvil"
```

---

## Script de análisis

Ejecutar desde la carpeta `stadiumflow/`:

```bash
python docs/analisis_validacion.py docs/validacion_resultados.csv
```
