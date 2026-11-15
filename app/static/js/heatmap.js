/**
 * heatmap.js — dibuja el recinto del estadio como SVG inline.
 * Coordenadas y puestos vienen del snapshot de la simulación.
 */

const LEVEL_COLORS = { green: '#16a34a', yellow: '#d97706', red: '#dc2626', unknown: '#9ca3af' };
const GREEN_MAX = 3, YELLOW_MAX = 6;

function getLevel(waitMin) {
  if (waitMin === null || waitMin === undefined || waitMin >= 999) return 'unknown';
  if (waitMin < GREEN_MAX)  return 'green';
  if (waitMin < YELLOW_MAX) return 'yellow';
  return 'red';
}

function svgEl(tag, attrs, text) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  if (text !== undefined) {
    const t = document.createTextNode(text);
    el.appendChild(t);
  }
  return el;
}

export function drawHeatmap(svgEl_, standKpis) {
  const svg = svgEl_;
  // Limpiar
  while (svg.firstChild) svg.removeChild(svg.firstChild);

  // Fondo
  svg.appendChild(svgEl('rect', { x: 0, y: 0, width: 850, height: 450, fill: '#f7f8fa' }));

  // Óvalo exterior del estadio
  svg.appendChild(svgEl('ellipse', { cx: 425, cy: 225, rx: 390, ry: 210, fill: 'none', stroke: '#1F3A5F', 'stroke-width': 3 }));

  // Campo de juego (rectángulo central)
  svg.appendChild(svgEl('rect', { x: 175, y: 110, width: 500, height: 230, rx: 30, fill: '#4ade80', stroke: '#166534', 'stroke-width': 2 }));

  // Línea de centro
  svg.appendChild(svgEl('line', { x1: 425, y1: 110, x2: 425, y2: 340, stroke: '#166534', 'stroke-width': 1.5 }));

  // Accesos A-D
  const accesses = [
    { label: 'A', x: 425, y: 15 }, { label: 'B', x: 800, y: 225 },
    { label: 'C', x: 425, y: 435 }, { label: 'D', x: 50, y: 225 },
  ];
  for (const ac of accesses) {
    const g = svgEl('g', {});
    g.appendChild(svgEl('rect', { x: ac.x - 14, y: ac.y - 12, width: 28, height: 24, rx: 4, fill: '#1F3A5F' }));
    const t = svgEl('text', { x: ac.x, y: ac.y + 5, fill: '#fff', 'font-size': 12, 'text-anchor': 'middle', 'font-family': 'sans-serif' });
    t.textContent = ac.label;
    g.appendChild(t);
    svg.appendChild(g);
  }

  // Puestos — usar datos del snapshot si existen
  const kpiMap = {};
  if (standKpis) {
    for (const k of standKpis) kpiMap[k.stand_id] = k;
  }

  // Posiciones estáticas de los 10 puestos (coinciden con default_match.json)
  const STAND_POSITIONS = {
    P1:  { x: 200, y: 50  }, P2:  { x: 350, y: 30  }, P3:  { x: 500, y: 30  },
    P4:  { x: 650, y: 50  }, P5:  { x: 750, y: 200 }, P6:  { x: 650, y: 370 },
    P7:  { x: 500, y: 400 }, P8:  { x: 350, y: 400 }, P9:  { x: 200, y: 370 },
    P10: { x: 100, y: 200 },
  };

  for (const [standId, pos] of Object.entries(STAND_POSITIONS)) {
    const kpi = kpiMap[standId];
    const wait = kpi ? kpi.estimated_wait_min : null;
    const level = getLevel(wait);
    const color = LEVEL_COLORS[level];
    const label = wait !== null && wait < 999 ? `${wait.toFixed(1)}m` : '—';

    const g = svgEl('g', { role: 'img', 'aria-label': `${standId}: espera ${label}` });
    g.appendChild(svgEl('rect', { x: pos.x - 22, y: pos.y - 14, width: 44, height: 28, rx: 5, fill: color, stroke: '#fff', 'stroke-width': 1.5 }));
    const t1 = svgEl('text', { x: pos.x, y: pos.y - 1, fill: '#fff', 'font-size': 10, 'text-anchor': 'middle', 'font-family': 'sans-serif', 'font-weight': 'bold' });
    t1.textContent = standId;
    g.appendChild(t1);
    const t2 = svgEl('text', { x: pos.x, y: pos.y + 11, fill: '#fff', 'font-size': 9, 'text-anchor': 'middle', 'font-family': 'sans-serif' });
    t2.textContent = label;
    g.appendChild(t2);
    svg.appendChild(g);
  }

  // Leyenda
  const legendData = [
    { label: '< 3 min', color: LEVEL_COLORS.green },
    { label: '3–6 min', color: LEVEL_COLORS.yellow },
    { label: '> 6 min', color: LEVEL_COLORS.red },
  ];
  let lx = 20;
  for (const ld of legendData) {
    const g = svgEl('g', {});
    g.appendChild(svgEl('rect', { x: lx, y: 420, width: 12, height: 12, fill: ld.color, rx: 2 }));
    const t = svgEl('text', { x: lx + 16, y: 431, 'font-size': 10, fill: '#57606a', 'font-family': 'sans-serif' });
    t.textContent = ld.label;
    g.appendChild(t);
    svg.appendChild(g);
    lx += 80;
  }
}
