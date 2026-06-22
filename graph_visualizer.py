"""Generate a dependency-free interactive HTML view of the architecture graph."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def export_interactive_html(graph_data: dict[str, Any], destination: str | Path) -> Path:
    """Embed NetworkX node-link data into a portable SVG-based visualizer."""

    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(graph_data).replace("</", "<\\/")
    template = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Architectural Memory Graph</title>
  <style>
    :root { color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }
    * { box-sizing: border-box; }
    body { margin: 0; min-height: 100vh; overflow: hidden; background: #07111f; color: #e6edf7; }
    .shell { display: grid; grid-template-columns: minmax(0, 1fr) 320px; height: 100vh; }
    main { position: relative; background: radial-gradient(circle at 45% 40%, #12263f 0, #07111f 56%); }
    header { position: absolute; z-index: 2; top: 26px; left: 30px; pointer-events: none; }
    h1 { margin: 0; font-size: 22px; letter-spacing: -.02em; }
    header p { margin: 7px 0 0; color: #8da2bc; font-size: 13px; }
    .toolbar { position: absolute; z-index: 2; top: 24px; right: 24px; display: flex; gap: 8px; }
    button { border: 1px solid #29445f; border-radius: 9px; padding: 8px 11px; background: #10233a; color: #dce8f7; cursor: pointer; }
    button:hover { border-color: #50d6c4; }
    svg { display: block; width: 100%; height: 100%; cursor: grab; }
    svg:active { cursor: grabbing; }
    .edge { stroke: #50708e; stroke-width: 2; opacity: .75; }
    .node { cursor: pointer; }
    .node circle { fill: #102d48; stroke: #4de0ca; stroke-width: 2.5; filter: drop-shadow(0 7px 14px #0008); transition: .18s; }
    .node:hover circle, .node.selected circle { fill: #174461; stroke: #ffd166; stroke-width: 4; }
    .node text { fill: #f5f9ff; font-size: 13px; font-weight: 650; text-anchor: middle; pointer-events: none; }
    aside { border-left: 1px solid #1d354d; padding: 27px 25px; background: #0b1929; overflow: auto; }
    .eyebrow { color: #4de0ca; font-size: 11px; font-weight: 750; letter-spacing: .14em; text-transform: uppercase; }
    aside h2 { margin: 9px 0 22px; font-size: 20px; word-break: break-word; }
    .stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 25px; }
    .stat { padding: 13px; border: 1px solid #1d3852; border-radius: 10px; background: #0e2135; }
    .stat strong { display: block; font-size: 20px; }
    .stat span, .hint { color: #8299b3; font-size: 12px; }
    .section { margin-top: 20px; }
    .section h3 { margin: 0 0 8px; color: #8da2bc; font-size: 11px; letter-spacing: .12em; text-transform: uppercase; }
    ul { margin: 0; padding-left: 18px; color: #dce8f7; }
    li { margin: 5px 0; }
    .doc { color: #b7c6d8; line-height: 1.55; }
    .empty { color: #70869f; font-style: italic; }
    .legend { position: absolute; left: 30px; bottom: 26px; color: #7890aa; font-size: 12px; }
    @media (max-width: 760px) { .shell { grid-template-columns: 1fr; grid-template-rows: 65vh 35vh; } aside { border-left: 0; border-top: 1px solid #1d354d; } }
  </style>
</head>
<body>
  <div class="shell">
    <main>
      <header><h1>Architectural Memory Graph</h1><p>Static-analysis ground truth · click a module to inspect it</p></header>
      <div class="toolbar"><button id="zoom-in" aria-label="Zoom in">＋</button><button id="zoom-out" aria-label="Zoom out">−</button><button id="reset">Reset</button></div>
      <svg id="graph" role="img" aria-label="Interactive module dependency graph">
        <defs><marker id="arrow" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8 Z" fill="#50708e"/></marker></defs>
        <g id="viewport"><g id="edges"></g><g id="nodes"></g></g>
      </svg>
      <div class="legend">Arrows represent resolved local imports. Drag nodes or the canvas to explore.</div>
    </main>
    <aside>
      <div class="eyebrow">Graph overview</div>
      <h2 id="title">Select a module</h2>
      <div class="stat-grid"><div class="stat"><strong id="node-count">0</strong><span>modules</span></div><div class="stat"><strong id="edge-count">0</strong><span>local imports</span></div></div>
      <div id="details" class="hint">Choose any node to see its functions, classes, imports, and module docstring.</div>
    </aside>
  </div>
  <script>
    const data = __GRAPH_DATA__;
    const svg = document.querySelector('#graph');
    const viewport = document.querySelector('#viewport');
    const nodesLayer = document.querySelector('#nodes');
    const edgesLayer = document.querySelector('#edges');
    document.querySelector('#node-count').textContent = data.nodes.length;
    document.querySelector('#edge-count').textContent = data.links.length;

    const width = 900, height = 650;
    const positions = new Map();
    data.nodes.forEach((node, index) => {
      const angle = (Math.PI * 2 * index / Math.max(data.nodes.length, 1)) - Math.PI / 2;
      const radius = data.nodes.length === 1 ? 0 : Math.min(220, 95 + data.nodes.length * 28);
      positions.set(node.id, { x: width / 2 + Math.cos(angle) * radius, y: height / 2 + Math.sin(angle) * radius });
    });

    const ns = 'http://www.w3.org/2000/svg';
    const edgeEls = data.links.map(link => {
      const line = document.createElementNS(ns, 'line');
      line.setAttribute('class', 'edge'); line.setAttribute('marker-end', 'url(#arrow)');
      edgesLayer.appendChild(line); return { line, link };
    });
    const nodeEls = new Map();
    data.nodes.forEach(node => {
      const group = document.createElementNS(ns, 'g'); group.setAttribute('class', 'node'); group.setAttribute('tabindex', '0');
      const circle = document.createElementNS(ns, 'circle'); circle.setAttribute('r', '48');
      const label = document.createElementNS(ns, 'text');
      const parts = node.id.split('/'); label.textContent = parts[parts.length - 1]; label.setAttribute('dy', '5');
      group.append(circle, label); nodesLayer.appendChild(group); nodeEls.set(node.id, group);
      group.addEventListener('click', event => { event.stopPropagation(); selectNode(node, group); });
      group.addEventListener('keydown', event => { if (event.key === 'Enter') selectNode(node, group); });
      makeDraggable(group, node.id);
    });

    function linkId(value) { return typeof value === 'object' ? value.id : value; }
    function render() {
      nodeEls.forEach((element, id) => { const p = positions.get(id); element.setAttribute('transform', `translate(${p.x} ${p.y})`); });
      edgeEls.forEach(({line, link}) => {
        const a = positions.get(linkId(link.source)), b = positions.get(linkId(link.target));
        const dx = b.x - a.x, dy = b.y - a.y, distance = Math.hypot(dx, dy) || 1;
        const pad = 54; line.setAttribute('x1', a.x + dx / distance * pad); line.setAttribute('y1', a.y + dy / distance * pad);
        line.setAttribute('x2', b.x - dx / distance * pad); line.setAttribute('y2', b.y - dy / distance * pad);
      });
    }
    function list(values) { return values?.length ? `<ul>${values.map(v => `<li>${escapeHtml(v)}</li>`).join('')}</ul>` : '<div class="empty">None</div>'; }
    function escapeHtml(value) { const div = document.createElement('div'); div.textContent = String(value); return div.innerHTML; }
    function selectNode(node, element) {
      nodeEls.forEach(el => el.classList.remove('selected')); element.classList.add('selected');
      document.querySelector('#title').textContent = node.id;
      document.querySelector('#details').innerHTML = `<div class="section"><h3>Functions</h3>${list(node.functions)}</div><div class="section"><h3>Classes</h3>${list(node.classes)}</div><div class="section"><h3>Imports</h3>${list(node.imports)}</div><div class="section"><h3>Docstring</h3><div class="doc">${node.docstring ? escapeHtml(node.docstring) : '<span class="empty">None</span>'}</div></div>`;
    }

    let transform = { x: 0, y: 0, scale: 1 };
    function applyTransform() { viewport.setAttribute('transform', `translate(${transform.x} ${transform.y}) scale(${transform.scale})`); }
    function zoom(factor) { transform.scale = Math.max(.4, Math.min(2.5, transform.scale * factor)); applyTransform(); }
    document.querySelector('#zoom-in').onclick = () => zoom(1.2); document.querySelector('#zoom-out').onclick = () => zoom(.8);
    document.querySelector('#reset').onclick = () => { transform = {x: 0, y: 0, scale: 1}; applyTransform(); };
    svg.addEventListener('wheel', event => { event.preventDefault(); zoom(event.deltaY < 0 ? 1.1 : .9); }, {passive: false});
    let pan = null;
    svg.addEventListener('pointerdown', event => { if (event.target === svg) pan = {x: event.clientX, y: event.clientY, tx: transform.x, ty: transform.y}; });
    svg.addEventListener('pointermove', event => { if (pan) { transform.x = pan.tx + event.clientX - pan.x; transform.y = pan.ty + event.clientY - pan.y; applyTransform(); } });
    svg.addEventListener('pointerup', () => pan = null); svg.addEventListener('pointerleave', () => pan = null);
    function makeDraggable(element, id) {
      let start = null;
      element.addEventListener('pointerdown', event => { event.stopPropagation(); start = {x: event.clientX, y: event.clientY, p: {...positions.get(id)}}; element.setPointerCapture(event.pointerId); });
      element.addEventListener('pointermove', event => { if (!start) return; positions.set(id, {x: start.p.x + (event.clientX-start.x)/transform.scale, y: start.p.y + (event.clientY-start.y)/transform.scale}); render(); });
      element.addEventListener('pointerup', () => start = null);
    }
    render();
    if (data.nodes[0]) selectNode(data.nodes[0], nodeEls.get(data.nodes[0].id));
    const fit = () => { const rect = svg.getBoundingClientRect(); transform = { x: (rect.width-width)/2, y: (rect.height-height)/2, scale: 1 }; applyTransform(); };
    fit();
  </script>
</body>
</html>'''
    path.write_text(template.replace("__GRAPH_DATA__", payload), encoding="utf-8")
    return path

