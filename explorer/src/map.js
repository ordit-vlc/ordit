/* Coropleta de la Comunitat Valenciana per a l'explorador.
   Acoloreix els poligons municipals (GISCO LAU, codi_ine) segons la capa triada:
   diners de la PAC (€), superficie de cultiu (ha) o ajuda per hectarea (€/ha). La vista
   pot agregar per comarca (acolorint cada municipi pel total de la seua comarca) o per
   municipi. Sense fusionar geometries.

   Accessibilitat (design system): rampa blava seqüencial per trams discrets (sense
   patro), llegenda numerica, valor al focus, llista lateral sempre visible; mai
   roig-verd; el color mai es l'unica senyal (acompanyat de llista i etiqueta). */

import { fmtEur, fmtHa, fmtEurHa } from "./format.js";

const SEQ = ["--seq-0", "--seq-1", "--seq-2", "--seq-3", "--seq-4", "--seq-5", "--seq-6"];
const CATS = ["--cat-1", "--cat-2", "--cat-3", "--cat-4", "--cat-5", "--cat-6"];

// Capes del mapa: etiqueta visible (valencia), titol i formatador del valor. Les capes de
// superficie venen del creuat SIGPAC x FEGA per municipi (campanya 2025, no filtrable).
export const LAYERS = {
  diners: { label: "Diners PAC", title: "Import de PAC", fmt: fmtEur, sigpac: false },
  superficie: { label: "Superficie", title: "Superficie agraria", fmt: fmtHa, sigpac: true },
  eur_ha: { label: "€/ha", title: "Ajuda per hectarea", fmt: fmtEurHa, sigpac: true },
};
export const layerFmt = (layer) => (LAYERS[layer] || LAYERS.diners).fmt;

const esc = (s) =>
  String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

function rings(geom) {
  if (geom.type === "Polygon") return geom.coordinates;
  if (geom.type === "MultiPolygon") return geom.coordinates.flat();
  return [];
}

/** Carrega el GeoJSON i precalcula el path SVG de cada municipi (projeccio equirectangular). */
export async function loadGeo(url) {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`No s'ha pogut llegir la geometria (${resp.status}).`);
  const features = (await resp.json()).features;
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const f of features)
    for (const r of rings(f.geometry))
      for (const [x, y] of r) {
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
        if (y < minY) minY = y;
        if (y > maxY) maxY = y;
      }
  const kx = Math.cos((((minY + maxY) / 2) * Math.PI) / 180); // correccio d'aspecte
  const W = 1000;
  const H = Math.round((W * (maxY - minY)) / ((maxX - minX) * kx));
  const px = (x) => (((x - minX) * kx) / ((maxX - minX) * kx)) * W;
  const py = (y) => ((maxY - y) / (maxY - minY)) * H;
  for (const f of features) {
    f._d = rings(f.geometry)
      .map((r) => "M" + r.map(([x, y]) => `${px(x).toFixed(1)} ${py(y).toFixed(1)}`).join("L") + "Z")
      .join("");
  }
  return { features, W, H };
}

function quantiles(values) {
  // 6 llindars -> 7 trams, sobre els valors positius (escala robusta a la asimetria).
  const v = values.filter((x) => x > 0).sort((a, b) => a - b);
  if (!v.length) return [];
  return [1, 2, 3, 4, 5, 6].map((i) => v[Math.min(v.length - 1, Math.floor((i / 7) * v.length))]);
}
function bucket(value, thresholds) {
  if (value <= 0) return -1; // sense dada
  let b = 0;
  while (b < thresholds.length && value > thresholds[b]) b += 1;
  return b;
}

/* El valor d'un municipi/comarca segons la capa triada.
   - diners: agg.byIne / agg.byComarca (files de FEGA filtrades).
   - superficie / eur_ha: surf, agregat estatic del creuat SIGPAC x FEGA per municipi.
     L'eur_ha de comarca es recalcula com a suma(import)/suma(superficie), no com a mitjana
     de ratios (que falsejaria el creuat). */
function valueFn(agg, surf, mapBy, layer) {
  if (layer === "diners") {
    return mapBy === "comarca"
      ? (f) => agg.byComarca.get(f.properties.comarca) || 0
      : (f) => agg.byIne.get(f.properties.codi_ine) || 0;
  }
  if (mapBy === "comarca") {
    return (f) => {
      const c = surf.byComarca.get(f.properties.comarca);
      if (!c) return 0;
      return layer === "superficie" ? c.sup : c.sup > 0 ? c.imp / c.sup : 0;
    };
  }
  return (f) => {
    const m = surf.byIne.get(f.properties.codi_ine);
    if (!m) return 0;
    return layer === "superficie" ? m.sup : m.eurHa;
  };
}

/** Desglossament de superficie per us d'un municipi seleccionat (card del lateral). */
function breakdownHtml(sel) {
  if (!sel) return "";
  if (!sel.rows || !sel.rows.length) {
    return `<div class="map-breakdown">
      <div class="mb-head"><span class="mb-title">${esc(sel.name)}</span>
        <button class="btn btn-ghost btn-sm" id="muni-clear" aria-label="Tanca el desglossament">✕</button></div>
      <p class="mono" style="color:var(--ink-3)">Sense superficie de cultiu de SIGPAC per a este municipi.</p>
    </div>`;
  }
  // El total "de cultiu" suma NOMES els usos agraris (es_agrari), de manera que quadra amb
  // la superficie_agraria_ha del llistat i la coropleta. Els usos no agraris (aigua, urba,
  // improductiu, forestal...) es mostren a banda com a subtotal, mai dins del total.
  const sorted = [...sel.rows].sort((a, b) => b.superficie_ha - a.superficie_ha);
  const agraris = sorted.filter((r) => r.es_agrari);
  const noAgraris = sorted.filter((r) => !r.es_agrari);
  // Total de cultiu: la superficie_agraria_ha autoritativa (mateixa font que el llistat i la
  // coropleta), per a quadrar exacte. Nomes si no arriba, es resumeix dels usos agraris.
  const sumAgraris = agraris.reduce((a, r) => a + r.superficie_ha, 0);
  const totalCultiu = sel.totalCultiu ?? sumAgraris;
  const totalNoAgrari = noAgraris.reduce((a, r) => a + r.superficie_ha, 0);
  // Escala de barres compartida (max sobre tots els usos) per a comparar-los honestament.
  const max = sorted.reduce((m, r) => Math.max(m, r.superficie_ha), 1);
  const rowHtml = (r, i, cat) => {
    const w = (r.superficie_ha / max) * 100;
    return `<div class="mb-row">
      <span class="mb-us" title="${esc(r.us)}">${esc(r.us)}</span>
      <div class="mb-track"><i style="width:${w}%;background:var(${cat})"></i></div>
      <span class="mb-val tnum">${fmtHa(r.superficie_ha)}</span></div>`;
  };
  const cultiuList = agraris.length
    ? agraris.map((r, i) => rowHtml(r, i, CATS[i % CATS.length])).join("")
    : `<p class="mono" style="color:var(--ink-3)">Sense usos agraris a SIGPAC.</p>`;
  const noAgrariBlock = noAgraris.length
    ? `<div class="mb-divider mono">No agrari (fora del total de cultiu) · subtotal ${fmtHa(totalNoAgrari)}</div>
       <div class="mb-list mb-noagr-list">${noAgraris.map((r) => rowHtml(r, 0, "--neutral")).join("")}</div>`
    : "";
  return `<div class="map-breakdown">
    <div class="mb-head"><span class="mb-title">${esc(sel.name)}</span>
      <button class="btn btn-ghost btn-sm" id="muni-clear" aria-label="Tanca el desglossament">✕</button></div>
    <div class="mb-sub mono">Superficie de cultiu · SIGPAC 2025 · total ${fmtHa(totalCultiu)}</div>
    <div class="mb-list">${cultiuList}</div>
    ${noAgrariBlock}
  </div>`;
}

/** HTML de la vista de mapa.
   ctx = {agg, surf, mapBy, layer, sel}. agg = {byIne, byComarca, unresolved} (diners);
   surf = {byIne: Map ine->{sup,imp,eurHa}, byComarca: Map->{sup,imp}}; sel = desglossament. */
export function mapHtml(geo, ctx) {
  const { agg, surf, mapBy, layer, sel } = ctx;
  const meta = LAYERS[layer] || LAYERS.diners;
  const fmt = meta.fmt;
  const valueOf = valueFn(agg, surf, mapBy, layer);
  const thresholds = quantiles(geo.features.map(valueOf));

  const tiles = geo.features
    .map((f) => {
      const v = valueOf(f);
      const b = bucket(v, thresholds);
      const fill = b < 0 ? "var(--paper-inset)" : `var(${SEQ[b]})`;
      const name = mapBy === "comarca" ? f.properties.comarca : f.properties.municipi;
      const isSel = sel && sel.ine === f.properties.codi_ine ? " is-sel" : "";
      return `<path d="${f._d}" class="map-tile${isSel}" tabindex="0" role="button"
        data-ine="${esc(f.properties.codi_ine)}" data-muni="${esc(f.properties.municipi)}"
        data-name="${esc(name)}" data-val="${v}" fill="${fill}"
        aria-label="${esc(name)}: ${esc(fmt(v))}"><title>${esc(name)} · ${esc(fmt(v))}</title></path>`;
    })
    .join("");

  // Llegenda numerica (trams discrets).
  const edges = [0, ...thresholds];
  const legend = SEQ.map((s, i) => {
    const lo = edges[i];
    const hi = i < thresholds.length ? thresholds[i] : null;
    const range = hi == null ? `> ${fmt(lo)}` : `${fmt(lo)} – ${fmt(hi)}`;
    return `<span class="leg-item"><i style="background:var(${s})"></i> ${esc(range)}</span>`;
  }).join("");

  // Llista lateral sempre visible (rang per valor); per a diners inclou els no resolts.
  const entries =
    mapBy === "comarca"
      ? geo.features.reduce((acc, f) => {
          const c = f.properties.comarca;
          if (!acc.seen.has(c)) {
            acc.seen.add(c);
            acc.out.push([c, valueOf(f)]);
          }
          return acc;
        }, { seen: new Set(), out: [] }).out
      : geo.features.map((f) => [f.properties.municipi, valueOf(f)]);
  const ranked = entries.filter(([, v]) => v !== 0).sort((a, b) => b[1] - a[1]);
  const list = ranked
    .map(([name, v]) => {
      const b = bucket(v, thresholds);
      const sw = b < 0 ? "var(--paper-inset)" : `var(${SEQ[b]})`;
      return `<div class="map-row"><span class="sw" style="background:${sw}"></span>
        <span class="nm">${esc(name)}</span><span class="vl tnum">${esc(fmt(v))}</span></div>`;
    })
    .join("");
  const unres =
    layer === "diners" && agg.unresolved > 0
      ? `<div class="map-row map-unres"><span class="sw" style="background:var(--neutral)"></span>
        <span class="nm">(sense municipi)</span><span class="vl tnum">${esc(fmt(agg.unresolved))}</span></div>`
      : "";

  const sigpacNote = meta.sigpac
    ? `<div class="map-note mono">Capa de SIGPAC (campanya 2025): no respon als filtres d'exercici ni de fons.</div>`
    : "";

  return `<div class="card card-pad">
    <div class="cluster" style="justify-content:space-between;gap:var(--s-4);margin-bottom:var(--s-4)">
      <h3 style="font-size:var(--t-lg)">${meta.title} per ${mapBy === "comarca" ? "comarca" : "municipi"}</h3>
      <div class="cluster" style="gap:var(--s-4)">
        <div class="seg" role="group" aria-label="Capa">
          <button data-maplayer="diners" class="${layer === "diners" ? "active" : ""}" aria-pressed="${layer === "diners"}">Diners PAC</button>
          <button data-maplayer="superficie" class="${layer === "superficie" ? "active" : ""}" aria-pressed="${layer === "superficie"}">Superficie</button>
          <button data-maplayer="eur_ha" class="${layer === "eur_ha" ? "active" : ""}" aria-pressed="${layer === "eur_ha"}">€/ha</button>
        </div>
        <div class="seg" role="group" aria-label="Granularitat">
          <button data-mapby="comarca" class="${mapBy === "comarca" ? "active" : ""}" aria-pressed="${mapBy === "comarca"}">Comarca</button>
          <button data-mapby="municipi" class="${mapBy === "municipi" ? "active" : ""}" aria-pressed="${mapBy === "municipi"}">Municipi</button>
        </div>
      </div>
    </div>
    ${sigpacNote}
    <div class="ex-map">
      <div class="map-figure">
        <svg viewBox="0 0 ${geo.W} ${geo.H}" class="map-svg" role="group" aria-label="Mapa de la Comunitat Valenciana">${tiles}</svg>
        <div class="map-legend mono" aria-hidden="true">${legend}<span class="leg-item"><i style="background:var(--paper-inset)"></i> sense dada</span></div>
      </div>
      <div class="map-aside">
        <div class="map-focus mono" id="map-focus">Tria un municipi al mapa per veure'n els usos de cultiu.</div>
        ${breakdownHtml(sel)}
        <div class="map-list">${list}${unres}</div>
      </div>
    </div>
  </div>`;
}
