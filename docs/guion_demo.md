# Guion de Demostración — StadiumFlow AI

**Duración estimada:** 5–7 minutos  
**Requisito:** datos de demo cargados (`python seed.py`)

---

## Preparación (antes de la demo)

```bash
cd stadiumflow
.venv\Scripts\activate        # Windows
python seed.py                 # Carga escenarios y corrida de demo
uvicorn app.main:app --reload
# Abrir http://127.0.0.1:8000
```

---

## Guion paso a paso

### 1. Inicio (30 seg)
- Mostrar la pantalla de inicio.
- Señalar los 3 escenarios precargados en la tabla.
- Mencionar que todos los datos son sintéticos e ilustrativos.

### 2. Escenarios (45 seg)
- Ir a **Escenarios** → hacer clic en "Editar" en el escenario *Partido estándar*.
- Mostrar el formulario completo: General, Etapas, Puestos, Perfiles, Comportamiento.
- Destacar el pico del medio tiempo (prob. de compra = 0.55).
- Volver a la lista.

### 3. Simulación base (90 seg)
- Clic en **▶ Base** del escenario *Partido estándar*.
- En el panel: clic en **▶ Iniciar** (velocidad 10×).
- Señalar el mapa de calor: los puestos del norte (P2, P3) se ponen rojos al llegar al medio tiempo.
- Señalar los KPIs: "Fila más larga" y "Se van sin comprar" aumentan.
- Pausar en el medio tiempo y señalar la línea de tiempo resaltada.
- Señalar: "Sin intervención, los aficionados esperan más de 6 minutos en P2 y P3."

### 4. Agente IA (90 seg)
- Volver a Escenarios → clic en **🤖 Con agente** del mismo escenario.
- Iniciar la simulación (velocidad 4×).
- Esperar a que aparezca una recomendación en el panel derecho.
- Leer la recomendación en voz alta: motivo, acción, efecto esperado.
- Clic en **Aplicar** → señalar que el mapa de calor cambia.
- Señalar: "El agente probó la acción en el simulador antes de proponerla."
- Ir a **Agente IA** → mostrar la bitácora con el tiempo de respuesta y el proveedor.
- Demostrar la conversación: escribir "¿cuál es el puesto más saturado?"

### 5. Informes (60 seg)
- Ir a **Informes** → seleccionar *Partido estándar*, 5 réplicas → clic **Comparar**.
- Señalar la tabla: media ± desviación estándar.
- Destacar la reducción de espera en medio tiempo y la advertencia de hipótesis.
- Descargar CSV → abrir para mostrar los datos.
- Clic en **Exportar PDF** → mostrar la vista previa en el navegador.

### 6. Cierre (30 seg)
- "El proyecto implementa 6 herramientas del agente, comparación con réplicas y exportación."
- "El código está listo para conectarse a IBM watsonx Orchestrate con solo configurar el .env."
- Señalar el aviso de datos sintéticos en la aplicación.

---

## Datos de demo reproducibles

```bash
python seed.py          # Siempre produce el mismo resultado con semilla 42
```

La corrida de demo `demo-default-seed42` está disponible en `/api/runs/demo-default-seed42/result` inmediatamente.
