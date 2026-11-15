/**
 * recommendations.js — renderiza tarjetas de recomendaciones en el panel de simulación.
 */
import { api } from './api.js';

export function renderRecommendations(container, recommendations, runId, onAction) {
  // Limpiar nodos existentes de forma segura
  while (container.firstChild) container.removeChild(container.firstChild);

  if (!recommendations || recommendations.length === 0) {
    const p = document.createElement('p');
    p.className = 'empty-text';
    p.textContent = 'Sin recomendaciones pendientes.';
    container.appendChild(p);
    return;
  }

  for (const rec of recommendations) {
    const card = _buildCard(rec, runId, onAction);
    container.appendChild(card);
  }
}

function _buildCard(rec, runId, onAction) {
  const card = document.createElement('div');
  card.className = `rec-card rec-card--${rec.status}`;

  const header = document.createElement('div');
  header.className = 'rec-card__header';

  const badge = document.createElement('span');
  badge.className = `badge badge--${rec.status}`;
  badge.textContent = rec.status;

  const minute = document.createElement('span');
  minute.className = 'rec-card__minute';
  minute.textContent = `Min. ${rec.minute}`;

  header.appendChild(badge);
  header.appendChild(minute);
  card.appendChild(header);

  const motive = document.createElement('p');
  motive.className = 'rec-card__motive';
  motive.textContent = rec.motive;
  card.appendChild(motive);

  const summary = document.createElement('p');
  summary.className = 'rec-card__summary';
  summary.textContent = rec.summary;
  card.appendChild(summary);

  if (rec.expected_effect) {
    const eff = document.createElement('div');
    eff.className = 'rec-card__effect';
    const s1 = document.createElement('span');
    s1.textContent = `Espera: ${rec.expected_effect.avg_wait_before_min} → ${rec.expected_effect.avg_wait_after_min} min`;
    const s2 = document.createElement('span');
    s2.textContent = `Abandono: ${rec.expected_effect.abandonment_before_pct}% → ${rec.expected_effect.abandonment_after_pct}%`;
    eff.appendChild(s1);
    eff.appendChild(s2);
    card.appendChild(eff);
  }

  if (rec.status === 'pending') {
    const actions = document.createElement('div');
    actions.className = 'rec-card__actions';

    const btnApply = document.createElement('button');
    btnApply.className = 'btn btn--sm btn--primary';
    btnApply.textContent = 'Aplicar';
    btnApply.setAttribute('aria-label', `Aplicar recomendación ${rec.id}`);
    btnApply.addEventListener('click', async () => {
      try {
        await api.post(`/api/runs/${runId}/recommendations/${rec.id}/apply`, {});
        onAction();
      } catch (e) { alert('Error: ' + e.message); }
    });

    const btnDiscard = document.createElement('button');
    btnDiscard.className = 'btn btn--sm btn--secondary';
    btnDiscard.textContent = 'Descartar';
    btnDiscard.setAttribute('aria-label', `Descartar recomendación ${rec.id}`);
    btnDiscard.addEventListener('click', async () => {
      try {
        await api.post(`/api/runs/${runId}/recommendations/${rec.id}/discard`, {});
        onAction();
      } catch (e) { alert('Error: ' + e.message); }
    });

    actions.appendChild(btnApply);
    actions.appendChild(btnDiscard);
    card.appendChild(actions);
  }

  return card;
}
