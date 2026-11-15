/**
 * simulation.js — Controlador del panel de simulación.
 * Polling con POST /step, actualización del mapa de calor y KPIs.
 */
import { api } from './api.js';
import { drawHeatmap } from './heatmap.js';
import { renderRecommendations } from './recommendations.js';

export class SimulationController {
  constructor(runId) {
    this.runId = runId;
    this.intervalId = null;
    this.speed = 500;  // ms entre pasos
    this.playing = false;
    this.finished = false;
  }

  init() {
    // Cargar estado inicial
    this._refreshState();
  }

  togglePlay() {
    if (this.finished) return;
    if (this.playing) {
      this._pause();
    } else {
      this._play();
    }
  }

  _play() {
    if (this.finished) return;
    this.playing = true;
    document.getElementById('btn-play').textContent = '⏸ Pausar';
    this.intervalId = setInterval(() => this._tick(), this.speed);
  }

  _pause() {
    this.playing = false;
    document.getElementById('btn-play').textContent = '▶ Iniciar';
    clearInterval(this.intervalId);
    this.intervalId = null;
  }

  setSpeed(ms) {
    this.speed = parseInt(ms);
    if (this.playing) {
      this._pause();
      this._play();
    }
  }

  async stepN(n) {
    if (this.finished) return;
    this._pause();
    try {
      await this._doStep(n);
    } catch (e) {
      this._setStatus('Error: ' + e.message);
    }
  }

  async runToEnd() {
    if (this.finished) return;
    this._pause();
    this._setStatus('Ejecutando hasta el final…');
    try {
      const data = await api.post(`/api/runs/${this.runId}/run-to-end`, {});
      this._updateUI(data.snapshot, [], false, true);
    } catch (e) {
      this._setStatus('Error: ' + e.message);
    }
  }

  reset() {
    // Recargar la página para reiniciar (el servidor no mantiene hilos de simulación)
    window.location.reload();
  }

  async _tick() {
    try {
      const paused = await this._doStep(1);
      if (paused) this._pause();
    } catch (e) {
      this._pause();
      this._setStatus('Error: ' + e.message);
    }
  }

  async _doStep(minutes) {
    const data = await api.post(`/api/runs/${this.runId}/step`, { minutes });
    const pending = data.all_pending || data.recommendations || [];
    this._updateUI(data.snapshot, pending, data.paused, data.finished);
    if (data.finished) {
      this.finished = true;
      this._pause();
    }
    return data.paused;
  }

  async _refreshState() {
    try {
      const snap = await api.get(`/api/runs/${this.runId}/state`);
      this._updateUI(snap, [], false, false);
    } catch (_) {}
  }

  _updateUI(snap, pending, paused, finished) {
    if (!snap) return;

    // KPIs globales — usar textContent (no innerHTML)
    this._setText('kpi-avg-wait', snap.global_avg_wait_min?.toFixed(1) ?? '—');
    this._setText('kpi-max-queue', snap.global_max_queue ?? '—');
    this._setText('kpi-abandonment', snap.global_abandonment_rate != null
      ? (snap.global_abandonment_rate * 100).toFixed(1)
      : '—');
    this._setText('kpi-occupancy', snap.global_occupancy != null
      ? (snap.global_occupancy * 100).toFixed(1)
      : '—');

    // Mapa de calor
    const svgEl = document.getElementById('heatmap-svg');
    if (svgEl) drawHeatmap(svgEl, snap.stands);

    // Línea de tiempo
    document.querySelectorAll('.timeline-phase').forEach(el => {
      el.classList.toggle('timeline-phase--active', el.dataset.phase === snap.phase);
    });

    // Recomendaciones
    const recList = document.getElementById('rec-list');
    if (recList) {
      renderRecommendations(recList, pending, this.runId, () => this._refreshState());
    }

    // Estado
    if (finished) {
      this._setStatus(`Corrida finalizada · Min. ${snap.minute}`);
    } else if (paused) {
      this._setStatus(`⏸ Pausado — hay ${pending.length} recomendación(es) pendiente(s).`);
    } else {
      this._setStatus(`Min. ${snap.minute} · Fase: ${snap.phase}`);
    }
  }

  _setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = String(value);
  }

  _setStatus(msg) {
    const el = document.getElementById('sim-status');
    if (el) el.textContent = msg;
  }
}
