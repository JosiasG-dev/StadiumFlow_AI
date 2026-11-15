/**
 * charts.js — Gráficas de comparación con Chart.js.
 * Chart.js se carga desde /static/vendor/chart.umd.min.js (global `Chart`).
 */

let waitChart = null;
let abandonChart = null;

export function renderComparisonCharts(result) {
  const phases = result.phase_aggregates.map(p => p.phase);
  const baseWaits   = result.phase_aggregates.map(p => p.avg_wait_mean);
  const abandonBase = result.phase_aggregates.map(p => +(p.abandonment_mean * 100).toFixed(2));

  // Buscar valores del agente desde replica_results si están disponibles
  const agentWaits = _extractAgentPhaseMetric(result, 'avg_wait_min');
  const agentAbandons = _extractAgentPhaseMetric(result, 'abandonment_rate').map(v => +(v * 100).toFixed(2));

  _renderBarChart('chart-wait', 'Espera promedio por fase (min)', phases,
    { label: 'Base', data: baseWaits, color: '#1F3A5F' },
    { label: 'Agente', data: agentWaits, color: '#2563eb' }
  );

  _renderBarChart('chart-abandonment', 'Abandono por fase (%)', phases,
    { label: 'Base', data: abandonBase, color: '#dc2626' },
    { label: 'Agente', data: agentAbandons, color: '#f97316' }
  );
}

function _extractAgentPhaseMetric(result, metric) {
  if (!result.replica_results || result.replica_results.length === 0) return [];
  const phases = result.phase_aggregates.map(p => p.phase);
  const phaseValues = {};
  let count = 0;
  for (const replica of result.replica_results) {
    count++;
    for (const p of replica.agent.phases) {
      phaseValues[p.phase] = (phaseValues[p.phase] || 0) + (p[metric] || 0);
    }
  }
  return phases.map(ph => count > 0 ? +((phaseValues[ph] || 0) / count).toFixed(3) : 0);
}

function _renderBarChart(canvasId, title, labels, dataset1, dataset2) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  if (!window.Chart) return;

  const existing = waitChart && canvasId.includes('wait') ? waitChart : abandonChart;
  if (existing) existing.destroy();

  const chart = new window.Chart(canvas, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { label: dataset1.label, data: dataset1.data, backgroundColor: dataset1.color + 'cc' },
        { label: dataset2.label, data: dataset2.data, backgroundColor: dataset2.color + 'cc' },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        title: { display: true, text: title, color: '#1F3A5F', font: { size: 14 } },
        legend: { position: 'bottom' },
      },
      scales: {
        y: { beginAtZero: true },
      },
    },
  });

  if (canvasId.includes('wait')) waitChart = chart;
  else abandonChart = chart;
}
