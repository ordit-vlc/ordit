/* Explorador d'Ordit · ajudes de la PAC de la Comunitat Valenciana (tots els receptors).
   Tot client-side: DuckDB-WASM llig el Parquet del mart i la resta es filtra en memoria.
   Identificadors en angles ASCII; interficie en valencia. */

import * as duckdb from "https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@1.29.0/+esm";
import { loadGeo, mapHtml, layerFmt } from "./map.js";
import { fmtEur, fmtInt } from "./format.js";

// Rutes dels Parquet publicats (relatives a /explorer/), servits com a fitxers estatics.
const PARQUET_URL = new URL("../data/dist/mart_ajudes_pac.parquet", location.href).href;
const SUP_URL = new URL("../data/dist/mart_pac_x_superficie_municipi.parquet", location.href).href;
const USE_URL = new URL("../data/dist/mart_superficie_cultiu_municipi.parquet", location.href).href;
const GEO_URL = new URL("geo/municipis-cv.geojson", location.href).href;

// Procedencia, sempre visible (cap dada sense font).
const SOURCE = {
  font: "FEGA · Beneficiaris PAC",
  url: "https://www.fega.gob.es/es/datos-abiertos/consulta-de-beneficiarios-pac",
  data: "2026-06-02",
  llic: "CC BY 4.0",
  estat: "confirmat",
};

// Dimensions de la taula: agrupables i llevables. Les ACTIVES son el GROUP BY; en llevar-ne
// una, la taula suma per damunt d'ella (les files col.lapsen); en afegir-la, es desglossa.
// L'ordre aci es l'ordre de columnes. La columna de VALOR (import_eur) sempre hi es, sumada
// i no llevable.
const DIMENSIONS = [
  // Beneficiari: s'agrupa per la CLAU canonica (col.lapsa variants de forma de la mateixa
  // entitat); es mostra l'etiqueta representativa (nom_canonic), no la clau crua.
  { key: "clau_beneficiari", label: "Beneficiari", type: "text", strong: true, display: "nom_canonic" },
  { key: "municipi", label: "Municipi", type: "text" },
  { key: "comarca", label: "Comarca", type: "text" },
  { key: "mesura", label: "Mesura", type: "text" },
  { key: "fons", label: "Fons", type: "text" },
  { key: "exercici", label: "Exercici", type: "num" },
];
const VALUE = { key: "import_eur", label: "Import (€)", type: "num", strong: true };

// Etiquetes de l'estat d'enllac amb el registre de cooperatives (un possible MAI es llig
// com a fet). Vegeu int_enllac_cooperatives.
const ESTAT_LABELS = {
  match: "Confirmat (match)",
  possible: "Candidat (possible)",
  "no-match": "Sense enllac",
};

const FACETS = [
  { key: "exercici", title: "Exercici", search: false },
  { key: "fons", title: "Fons", search: false },
  { key: "estat_enllac", title: "Enllac cooperatives", search: false, labels: ESTAT_LABELS },
  { key: "comarca", title: "Comarca", search: true },
  { key: "municipi", title: "Municipi", search: true },
  { key: "mesura", title: "Mesura", search: true },
];

const TABLE_LIMIT = 300; // files mostrades a la taula (l'agregat i els KPI usen tot el filtrat)

const state = {
  rows: [],
  surf: { byIne: new Map(), byComarca: new Map() }, // creuat SIGPAC x FEGA per municipi
  useByIne: new Map(), // desglossament de superficie per us, per codi_ine
  canonLabel: new Map(), // clau_beneficiari -> nom_canonic (etiqueta representativa)
  linkByClau: new Map(), // clau_beneficiari -> {estat, cif, clauReg} (enllac cooperatives)
  geo: null,
  query: "",
  sel: {
    exercici: new Set(),
    fons: new Set(),
    estat_enllac: new Set(),
    comarca: new Set(),
    municipi: new Set(),
    mesura: new Set(),
  },
  facetSearch: { comarca: "", municipi: "", mesura: "" },
  // Estat del panell de filtres (recordat durant la sessio): panell sencer col.lapsat i
  // conjunt de facetes col.lapsades (acordio per seccio). Col.lapsar es nomes visual: els
  // filtres actius segueixen aplicant-se.
  asideCollapsed: false,
  collapsedFacets: new Set(),
  // Dimensions actives (GROUP BY de la taula). Per defecte totes -> maxima granularitat.
  dims: new Set(DIMENSIONS.map((d) => d.key)),
  sortKey: "import_eur",
  sortDir: "desc",
  view: "taula", // taula | mapa | grafic
  mapBy: "comarca", // comarca | municipi
  mapLayer: "diners", // diners | superficie | eur_ha (capa de la coropleta)
  selMuni: null, // {ine, name} del municipi triat al mapa (desglossament d'usos)
  chartBy: "municipi", // municipi | beneficiari
  density: "compacte",
};

// Agregat geografic per a la coropleta: import per codi_ine i per comarca, + no resolts.
function geoAgg(rows) {
  const byIne = new Map();
  const byComarca = new Map();
  let unresolved = 0;
  for (const r of rows) {
    if (r.codi_ine) {
      byIne.set(r.codi_ine, (byIne.get(r.codi_ine) || 0) + r.import_eur);
      byComarca.set(r.comarca, (byComarca.get(r.comarca) || 0) + r.import_eur);
    } else {
      unresolved += r.import_eur; // codi_ine NULL <=> comarca "(sense comarca)"
    }
  }
  return { byIne, byComarca, unresolved };
}

/* ---------- Carrega dels marts amb DuckDB-WASM ---------- */
async function registerParquet(db, name, url) {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`No s'ha pogut llegir ${name} (${resp.status}).`);
  await db.registerFileBuffer(name, new Uint8Array(await resp.arrayBuffer()));
}

// Carrega els tres marts publicats: ajudes de la PAC (files), creuat SIGPAC x FEGA per
// municipi (coropleta de superficie/€-ha) i superficie per us (desglossament municipal).
async function loadMarts() {
  const bundle = await duckdb.selectBundle(duckdb.getJsDelivrBundles());
  const workerUrl = URL.createObjectURL(
    new Blob([`importScripts("${bundle.mainWorker}");`], { type: "text/javascript" }),
  );
  const worker = new Worker(workerUrl);
  const db = new duckdb.AsyncDuckDB(new duckdb.ConsoleLogger(), worker);
  await db.instantiate(bundle.mainModule, bundle.pthreadWorker);
  URL.revokeObjectURL(workerUrl);

  await Promise.all([
    registerParquet(db, "ajudes.parquet", PARQUET_URL),
    registerParquet(db, "superficie.parquet", SUP_URL),
    registerParquet(db, "usos.parquet", USE_URL),
  ]);

  const conn = await db.connect();
  const ajudes = await conn.query(
    `select nom_beneficiari, clau_beneficiari, nom_canonic,
            coalesce(municipi, '(sense resoldre)') as municipi,
            coalesce(comarca, '(sense comarca)') as comarca,
            provincia, codi_postal, codi_ine, mesura,
            cast(import_eur as double) as import_eur, fons, exercici,
            group_cif, group_name, estat_enllac, cif, clau_registral
     from 'ajudes.parquet'`,
  );
  const superficie = await conn.query(
    `select codi_ine, comarca,
            cast(superficie_agraria_ha as double) as superficie_agraria_ha,
            cast(import_pac_eur as double) as import_pac_eur,
            cast(import_eur_per_ha as double) as import_eur_per_ha
     from 'superficie.parquet'`,
  );
  const usos = await conn.query(
    `select codi_ine, codi_us, us, es_agrari,
            cast(superficie_ha as double) as superficie_ha,
            cast(nombre_recintes as bigint) as nombre_recintes
     from 'usos.parquet'`,
  );
  await conn.close();
  return {
    rows: ajudes.toArray().map((r) => r.toJSON()),
    surfRows: superficie.toArray().map((r) => r.toJSON()),
    useRows: usos.toArray().map((r) => r.toJSON()),
  };
}

// Agregat estatic del creuat per municipi: byIne (superficie, import, €/ha) i byComarca
// (sumes; el €/ha de comarca es recalcula com a suma-import/suma-superficie a map.js).
function buildSurf(surfRows) {
  const byIne = new Map();
  const byComarca = new Map();
  for (const r of surfRows) {
    byIne.set(r.codi_ine, {
      sup: r.superficie_agraria_ha,
      imp: r.import_pac_eur,
      eurHa: r.import_eur_per_ha,
    });
    const c = byComarca.get(r.comarca) || { sup: 0, imp: 0 };
    c.sup += r.superficie_agraria_ha;
    c.imp += r.import_pac_eur;
    byComarca.set(r.comarca, c);
  }
  return { byIne, byComarca };
}

// Desglossament de superficie per us, indexat per codi_ine.
function buildUse(useRows) {
  const m = new Map();
  for (const r of useRows) {
    if (!m.has(r.codi_ine)) m.set(r.codi_ine, []);
    m.get(r.codi_ine).push(r);
  }
  return m;
}

/* ---------- Derivats ---------- */
function filteredRows() {
  const q = state.query.trim().toLowerCase();
  return state.rows.filter((r) => {
    for (const f of FACETS) {
      const sel = state.sel[f.key];
      if (sel.size && !sel.has(String(r[f.key]))) return false;
    }
    if (q && !r.nom_beneficiari.toLowerCase().includes(q) && !r.municipi.toLowerCase().includes(q)) {
      return false;
    }
    return true;
  });
}

function facetCounts(key) {
  // Recompte sobre les files que passen TOTS els altres filtres (no el propi).
  const q = state.query.trim().toLowerCase();
  const counts = new Map();
  for (const r of state.rows) {
    let ok = true;
    for (const f of FACETS) {
      if (f.key === key) continue;
      const sel = state.sel[f.key];
      if (sel.size && !sel.has(String(r[f.key]))) {
        ok = false;
        break;
      }
    }
    if (ok && q && !r.nom_beneficiari.toLowerCase().includes(q) && !r.municipi.toLowerCase().includes(q)) {
      ok = false;
    }
    if (!ok) continue;
    const v = String(r[key]);
    counts.set(v, (counts.get(v) || 0) + 1);
  }
  return counts;
}

function sortRows(rows) {
  const { sortKey, sortDir } = state;
  const dir = sortDir === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => {
    const av = a[sortKey];
    const bv = b[sortKey];
    if (typeof av === "string") return av.localeCompare(bv, "ca") * dir;
    return (av - bv) * dir;
  });
}

function aggregate(rows, key) {
  const agg = new Map();
  for (const r of rows) agg.set(r[key], (agg.get(r[key]) || 0) + r.import_eur);
  return [...agg.entries()].map(([k, v]) => ({ k, v })).sort((a, b) => b.v - a.v);
}

// Agrupa les files filtrades per les dimensions actives (GROUP BY) i suma import_eur. Cap
// dimensio activa -> una sola fila de total general. Filtrar i agrupar son coses distintes:
// les files ja venen filtrades; aci nomes s'agrupen. Tot en memoria, cap crida de xarxa.
function groupRows(rows, dimKeys) {
  if (!dimKeys.length) {
    return [{ import_eur: rows.reduce((a, r) => a + r.import_eur, 0) }];
  }
  const groups = new Map();
  for (const r of rows) {
    const key = dimKeys.map((d) => r[d]).join("\u0001"); // separador de control, no apareix als valors
    let g = groups.get(key);
    if (!g) {
      g = { import_eur: 0 };
      for (const d of dimKeys) g[d] = r[d];
      groups.set(key, g);
    }
    g.import_eur += r.import_eur;
  }
  return [...groups.values()];
}

/* ---------- Render ---------- */
const esc = (s) =>
  String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

function provHtml(compact) {
  const dot = SOURCE.estat === "confirmat" ? "var(--ok)" : "var(--avis)";
  const tail = compact ? "" : ` · ${SOURCE.data} · ${SOURCE.llic}`;
  return `<span class="prov" title="Estat: ${SOURCE.estat}">
    <span class="prov-key"><span class="prov-dot" style="background:${dot}"></span> Font</span>
    <span class="prov-val"><a href="${SOURCE.url}" target="_blank" rel="noopener">${esc(SOURCE.font)}</a>${tail}</span>
  </span>`;
}

function facetHtml(f) {
  const counts = facetCounts(f.key);
  const sel = state.sel[f.key];
  let opts = [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "ca"));
  if (f.search && state.facetSearch[f.key]) {
    const fq = state.facetSearch[f.key].toLowerCase();
    opts = opts.filter(([v]) => v.toLowerCase().includes(fq));
  }
  const shown = opts.slice(0, f.search ? 80 : 50);
  const collapsed = state.collapsedFacets.has(f.key);
  // Capcalera com a boto: accessible amb teclat (Tab + Enter/Espai), aria-expanded i
  // aria-controls cap al cos. El chevron es nomes una pista visual (aria-hidden).
  const head = `<button type="button" class="facet-head" data-facet-toggle="${f.key}"
      aria-expanded="${!collapsed}" aria-controls="facet-body-${f.key}">
    <span class="facet-title">${f.title}</span>
    <span class="facet-meta">
      <span class="mono">${sel.size ? sel.size + " sel." : counts.size}</span>
      <span class="facet-chevron" aria-hidden="true">${collapsed ? "▸" : "▾"}</span>
    </span></button>`;
  const searchBox = f.search
    ? `<input class="input facet-search" data-facet="${f.key}" placeholder="filtra ${f.title.toLowerCase()}…"
        value="${esc(state.facetSearch[f.key])}" aria-label="Filtra ${f.title}" />`
    : "";
  const list = shown
    .map(
      ([v, n]) => `<label class="facet-opt">
        <input type="checkbox" data-facet="${f.key}" value="${esc(v)}" ${sel.has(v) ? "checked" : ""} />
        <span class="opt-label">${esc(f.labels?.[v] ?? v)}</span><span class="opt-count">${n}</span></label>`,
    )
    .join("");
  const more = opts.length > shown.length ? `<div class="facet-more mono">+${opts.length - shown.length} mes…</div>` : "";
  const body = `<div class="facet-body" id="facet-body-${f.key}">${searchBox}<div class="facet-list">${list}${more}</div></div>`;
  return `<div class="facet${collapsed ? " is-collapsed" : ""}">${head}${body}</div>`;
}

function kpiHtml(rows) {
  const benef = new Set(rows.map((r) => r.clau_beneficiari)).size;
  const munis = new Set(rows.map((r) => r.municipi)).size;
  const total = rows.reduce((a, r) => a + r.import_eur, 0);
  return `<div class="ex-kpis">
    <div class="stat"><div class="stat-label">Beneficiaris</div><div class="stat-num tnum">${fmtInt(benef)}</div><div class="stat-sub">beneficiaris de la PAC</div></div>
    <div class="stat"><div class="stat-label">Ajudes</div><div class="stat-num tnum">${fmtInt(rows.length)}</div><div class="stat-sub">files (beneficiari·municipi·fons·mesura)</div></div>
    <div class="stat"><div class="stat-label">Import · €</div><div class="stat-num tnum">${fmtInt(total)}</div><div class="stat-sub">contribucio europea</div></div>
    <div class="stat"><div class="stat-label">Municipis</div><div class="stat-num tnum">${fmtInt(munis)}</div><div class="stat-sub">de la Comunitat Valenciana</div></div>
  </div>`;
}

function chipsHtml() {
  const chips = [];
  for (const f of FACETS) {
    for (const v of state.sel[f.key]) {
      const label = f.labels?.[v] ?? v;
      chips.push(`<span class="chip">${esc(label)}<button data-chip-facet="${f.key}" data-chip-val="${esc(v)}" aria-label="Lleva ${esc(label)}">✕</button></span>`);
    }
  }
  if (!chips.length) return "";
  return `<div class="cluster" style="margin-bottom:var(--s-4)">${chips.join("")}</div>`;
}

// Cel.la d'una dimensio segons el seu tipus (beneficiari fort, mesura ampla, fons en
// pastilla, exercici numeric). El valor pot ser undefined si la dimensio no esta agrupada,
// pero aci nomes es pinten columnes ACTIVES, aixi que sempre hi es.
// Badge d'enllac amb el registre de cooperatives. match = confirmat (verd); possible =
// candidat (ambre); MAI es llig un possible com a fet. Mostra CIF i clau registral.
function linkBadgeHtml(clau) {
  const link = state.linkByClau.get(clau);
  if (!link) return "";
  const cls = link.estat === "match" ? "badge-ok" : "badge-avis";
  const etiqueta = link.estat === "match" ? "✓ Coop." : "Coop.?";
  const title = `Enllac al Registre de Cooperatives de la CV · ${ESTAT_LABELS[link.estat]} · CIF ${link.cif}${link.clauReg ? " · " + link.clauReg : ""}`;
  return ` <span class="badge ${cls} link-badge" title="${esc(title)}">${etiqueta} ${esc(link.cif)}</span>`;
}

function dimCellHtml(col, r) {
  if (col.key === "fons") return `<td><span class="badge">${esc(r.fons)}</span></td>`;
  if (col.key === "mesura") return `<td class="cell-mesura">${esc(r.mesura)}</td>`;
  // Columnes amb etiqueta representativa (p. ex. beneficiari: clau -> nom_canonic).
  const text = col.display ? (state.canonLabel.get(r[col.key]) ?? r[col.key]) : r[col.key];
  // Al beneficiari, afig el badge d'enllac (CIF + estat) si esta enllacat.
  const badge = col.key === "clau_beneficiari" ? linkBadgeHtml(r[col.key]) : "";
  const cls = col.strong ? "cell-strong" : col.type === "num" ? "num" : "";
  return `<td${cls ? ` class="${cls}"` : ""}>${esc(text)}${badge}</td>`;
}

function tableHtml(rows) {
  const ind = (k) => (state.sortKey === k ? `<span class="sort-ind">${state.sortDir === "asc" ? "▲" : "▼"}</span>` : "");
  // Filtrar i agrupar son coses distintes: `rows` ja ve filtrat; aci s'agrupa per les
  // dimensions ACTIVES (GROUP BY) i es suma l'import. Despres s'ordena i es talla a top-N.
  const dimKeys = DIMENSIONS.filter((d) => state.dims.has(d.key)).map((d) => d.key);
  const cols = [...DIMENSIONS.filter((d) => state.dims.has(d.key)), VALUE];
  const grouped = sortRows(groupRows(rows, dimKeys));
  const max = grouped.reduce((m, r) => Math.max(m, Math.abs(r.import_eur)), 1);
  const head = cols
    .map((c) => `<th class="${c.type === "num" ? "num " : ""}sortable" data-sort="${c.key}">${c.label} ${ind(c.key)}</th>`)
    .join("");
  const shown = grouped.slice(0, TABLE_LIMIT);
  const body =
    shown
      .map((r) => {
        const bar = `<div class="cellbar"><i style="width:${(Math.abs(r.import_eur) / max) * 100}%"></i></div>`;
        const valCell = `<td class="num cell-strong">${fmtEur(r.import_eur)}${bar}</td>`;
        const dimCells = cols
          .filter((c) => c.key !== "import_eur")
          .map((c) => dimCellHtml(c, r))
          .join("");
        return `<tr>${dimCells}${valCell}</tr>`;
      })
      .join("") ||
    `<tr><td colspan="${cols.length}" style="text-align:center;padding:var(--s-7);color:var(--ink-3)">Cap ajuda coincideix amb els filtres.</td></tr>`;
  const unit = dimKeys.length === DIMENSIONS.length ? "files" : dimKeys.length ? "grups" : "total";
  const note =
    grouped.length > TABLE_LIMIT
      ? `mostrant ${TABLE_LIMIT} de ${fmtInt(grouped.length)} ${unit} (l'agregat i els KPI usen tot el filtrat)`
      : `${fmtInt(grouped.length)} ${unit}`;
  // Toggles de dimensio (multi-actiu): llevar/afegir = reagrupar, no nomes amagar.
  const dimToggles = DIMENSIONS.map(
    (d) => `<button data-dim="${d.key}" class="${state.dims.has(d.key) ? "active" : ""}" aria-pressed="${state.dims.has(d.key)}">${d.label}</button>`,
  ).join("");
  const sortedLabel = cols.find((c) => c.key === state.sortKey)?.label || VALUE.label;
  return `<div class="ex-tablebar">
      <div class="cluster" style="gap:.5rem;flex-wrap:wrap">
        <span class="mono" style="color:var(--ink-2)">Agrupa per</span>
        <div class="seg seg-wrap" role="group" aria-label="Dimensions agrupables">${dimToggles}</div>
      </div>
      <div class="ex-densitat cluster">
        <span class="mono">Densitat</span>
        <div class="seg">
          <button data-density="compacte" class="${state.density === "compacte" ? "active" : ""}" aria-pressed="${state.density === "compacte"}">Compacte</button>
          <button data-density="comode" class="${state.density === "comode" ? "active" : ""}" aria-pressed="${state.density === "comode"}">Comode</button>
        </div>
      </div>
    </div>
    <div class="table-wrap"><table class="data${state.density === "compacte" ? " compact" : ""}">
      <thead><tr>${head}</tr></thead><tbody>${body}</tbody>
    </table></div>
    <div class="pager" style="margin-top:var(--s-4)"><span class="info">${note} · ordenat per ${esc(sortedLabel)} (${state.sortDir})</span>${provHtml(false)}</div>`;
}

function chartHtml(rows) {
  const by = state.chartBy;
  // "Top receptors" agrega per clau canonica (no pel nom cru) i mostra l'etiqueta representativa.
  const byBenef = by !== "municipi";
  const data = aggregate(rows, byBenef ? "clau_beneficiari" : "municipi").slice(0, 15);
  const label = (k) => (byBenef ? (state.canonLabel.get(k) ?? k) : k);
  const max = Math.max(...data.map((d) => Math.abs(d.v)), 1);
  const cats = ["--cat-1", "--cat-2", "--cat-3", "--cat-4", "--cat-5", "--cat-6"];
  const bars = data
    .map(
      (d, i) => `<div class="barrow" style="grid-template-columns:220px 1fr auto">
      <span class="bl" title="${esc(label(d.k))}">${esc(label(d.k))}</span>
      <div class="bartrack"><div class="barfill" style="width:${(Math.abs(d.v) / max) * 100}%;background:var(${cats[i % cats.length]})"></div></div>
      <span class="bt tnum">${fmtEur(d.v)}</span></div>`,
    )
    .join("");
  return `<div class="card card-pad">
    <div class="cluster" style="justify-content:space-between;margin-bottom:var(--s-5)">
      <h3 style="font-size:var(--t-lg)">Import per ${by === "municipi" ? "municipi" : "beneficiari"} (top 15)</h3>
      <div class="seg">
        <button data-chartby="municipi" class="${by === "municipi" ? "active" : ""}" aria-pressed="${by === "municipi"}">Per municipi</button>
        <button data-chartby="beneficiari" class="${by === "beneficiari" ? "active" : ""}" aria-pressed="${by === "beneficiari"}">Top receptors</button>
      </div>
    </div>
    <div class="barchart">${bars}</div>
    <div style="margin-top:var(--s-5);border-top:1px solid var(--line-hair);padding-top:var(--s-4)">${provHtml(false)}</div>
  </div>`;
}

const MARK = `<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true">
  <line x1="3" y1="9" x2="3" y2="20"/><line x1="7.5" y1="5" x2="7.5" y2="20"/><line x1="12" y1="3" x2="12" y2="20"/><line x1="16.5" y1="5" x2="16.5" y2="20"/><line x1="21" y1="9" x2="21" y2="20"/></svg>`;

function render() {
  // Files filtrades (sense ordenar): la taula agrupa i ordena pel seu compte; el mapa, els
  // KPI i el grafic no depenen de l'ordre. Evita ordenar centenars de milers de files debades.
  const rows = filteredRows();
  const facets = FACETS.map(facetHtml).join("");
  const content =
    state.view === "taula"
      ? tableHtml(rows)
      : state.view === "mapa"
        ? mapHtml(state.geo, {
            agg: geoAgg(rows),
            surf: state.surf,
            mapBy: state.mapBy,
            layer: state.mapLayer,
            sel: state.selMuni
              ? {
                  ine: state.selMuni.ine,
                  name: state.selMuni.name,
                  rows: state.useByIne.get(state.selMuni.ine),
                  // Total de cultiu autoritatiu: la mateixa superficie_agraria_ha del llistat
                  // i la coropleta (font unica), no una resuma en JS dels usos.
                  totalCultiu: state.surf.byIne.get(state.selMuni.ine)?.sup,
                }
              : null,
          })
        : chartHtml(rows);
  document.getElementById("app").innerHTML = `
    <header class="ex-bar"><div class="ex-bar-inner">
      <a class="ordit-logo" href="#"><span class="ordit-mark">${MARK}</span><span class="ordit-word"><b>or</b>dit</span></a>
      <span class="badge" style="margin-left:.4rem">explorador</span>
      <div class="search" style="flex:1 1 320px;max-width:440px;margin-left:auto">
        <input class="input" id="q" value="${esc(state.query)}" placeholder="Cerca beneficiari o municipi…" aria-label="Cerca" />
      </div>
      <div class="cluster" style="gap:.5rem"><button class="btn btn-primary btn-sm" id="csv">Descarrega CSV</button></div>
    </div></header>
    <div class="ex-layout${state.asideCollapsed ? " aside-collapsed" : ""}">
      <aside class="ex-aside${state.asideCollapsed ? " is-collapsed" : ""}">
        <div class="ex-aside-head">
          <button type="button" class="btn btn-ghost btn-sm aside-toggle" id="aside-toggle"
            aria-expanded="${!state.asideCollapsed}" aria-controls="aside-body"
            title="${state.asideCollapsed ? "Mostra els filtres" : "Amaga els filtres"}"
            aria-label="${state.asideCollapsed ? "Mostra els filtres" : "Amaga els filtres"}">
            <span class="aside-chevron" aria-hidden="true">${state.asideCollapsed ? "»" : "«"}</span>
            <span class="mono">Filtres</span>
          </button>
          ${state.asideCollapsed ? "" : `<button class="btn btn-ghost btn-sm" id="clear">Neteja</button>`}
        </div>
        <div class="ex-aside-body" id="aside-body">${facets}</div>
      </aside>
      <main class="ex-main">
        ${kpiHtml(rows)}
        <div class="ex-controls">
          <div class="cluster"><span class="mono" style="margin-right:.2rem">Vista</span>
            <div class="seg">
              <button data-view="taula" class="${state.view === "taula" ? "active" : ""}" aria-pressed="${state.view === "taula"}">Taula</button>
              <button data-view="mapa" class="${state.view === "mapa" ? "active" : ""}" aria-pressed="${state.view === "mapa"}">Mapa</button>
              <button data-view="grafic" class="${state.view === "grafic" ? "active" : ""}" aria-pressed="${state.view === "grafic"}">Grafic</button>
            </div>
          </div>
          <div class="cluster" style="gap:.7rem">${provHtml(true)}<span class="status is-ok">Confirmat</span></div>
        </div>
        ${chipsHtml()}
        ${content}
      </main>
    </div>
    ${creditsHtml()}`;
}

// Atribucio de fonts, sempre visible (peu de credits a totes les vistes).
function creditsHtml() {
  return `<footer class="ex-credits mono">
    <span><strong>Fonts.</strong> Dades de la PAC:
      <a href="${SOURCE.url}" target="_blank" rel="noopener">FEGA</a> · ${SOURCE.llic}.</span>
    <span>Geometria de municipis: © EuroGeographics
      (<a href="https://ec.europa.eu/eurostat/web/gisco" target="_blank" rel="noopener">GISCO</a>/IGN), CC BY.</span>
    <span>Codis postals:
      <a href="https://www.geonames.org/" target="_blank" rel="noopener">GeoNames</a>, CC BY 4.0.</span>
  </footer>`;
}

/* ---------- Esdeveniments (delegacio) ---------- */
function setupEvents() {
  const app = document.getElementById("app");
  app.addEventListener("click", (e) => {
    const t = e.target.closest(
      "[data-sort],[data-view],[data-chartby],[data-density],[data-chip-facet],[data-dim]," +
        "[data-facet-toggle],[data-maplayer],[data-mapby],[data-muni],#clear,#aside-toggle,#muni-clear",
    );
    if (!t) return;
    // Despres del re-render, torna el focus al control col.lapsable (accessibilitat teclat).
    let refocus = null;
    if (t.dataset.facetToggle) {
      const k = t.dataset.facetToggle;
      state.collapsedFacets.has(k) ? state.collapsedFacets.delete(k) : state.collapsedFacets.add(k);
      refocus = `[data-facet-toggle="${k}"]`;
    } else if (t.id === "aside-toggle") {
      state.asideCollapsed = !state.asideCollapsed;
      refocus = "#aside-toggle";
    } else if (t.dataset.sort) {
      const k = t.dataset.sort;
      if (state.sortKey === k) state.sortDir = state.sortDir === "asc" ? "desc" : "asc";
      else {
        state.sortKey = k;
        state.sortDir = k === "import_eur" || k === "exercici" ? "desc" : "asc";
      }
    } else if (t.dataset.dim) {
      // Lleva/afig una dimensio del GROUP BY de la taula (reagrega).
      const k = t.dataset.dim;
      state.dims.has(k) ? state.dims.delete(k) : state.dims.add(k);
      // Si s'ordenava per una dimensio que s'acaba de llevar, torna a ordenar per import.
      if (!state.dims.has(state.sortKey) && state.sortKey !== "import_eur") {
        state.sortKey = "import_eur";
        state.sortDir = "desc";
      }
    } else if (t.dataset.view) state.view = t.dataset.view;
    else if (t.dataset.maplayer) state.mapLayer = t.dataset.maplayer;
    else if (t.dataset.mapby) state.mapBy = t.dataset.mapby;
    else if (t.dataset.muni) {
      // Tria/desmarca un municipi al mapa per al desglossament d'usos de cultiu.
      const ine = t.dataset.ine;
      state.selMuni = state.selMuni && state.selMuni.ine === ine ? null : { ine, name: t.dataset.muni };
    } else if (t.id === "muni-clear") state.selMuni = null;
    else if (t.dataset.chartby) state.chartBy = t.dataset.chartby;
    else if (t.dataset.density) state.density = t.dataset.density;
    else if (t.dataset.chipFacet) state.sel[t.dataset.chipFacet].delete(t.dataset.chipVal);
    else if (t.id === "clear") {
      for (const f of FACETS) state.sel[f.key].clear();
      state.query = "";
      for (const k of Object.keys(state.facetSearch)) state.facetSearch[k] = "";
    }
    render();
    if (refocus) document.querySelector(refocus)?.focus();
  });
  app.addEventListener("change", (e) => {
    const cb = e.target.closest('input[type="checkbox"][data-facet]');
    if (!cb) return;
    const set = state.sel[cb.dataset.facet];
    cb.checked ? set.add(cb.value) : set.delete(cb.value);
    render();
  });
  app.addEventListener("input", (e) => {
    if (e.target.id === "q") {
      state.query = e.target.value;
      render();
      const q = document.getElementById("q");
      q.focus();
      q.setSelectionRange(q.value.length, q.value.length);
    } else if (e.target.classList.contains("facet-search")) {
      state.facetSearch[e.target.dataset.facet] = e.target.value;
      const key = e.target.dataset.facet;
      render();
      const box = document.querySelector(`.facet-search[data-facet="${key}"]`);
      if (box) {
        box.focus();
        box.setSelectionRange(box.value.length, box.value.length);
      }
    }
  });
  app.addEventListener("click", (e) => {
    if (e.target.id === "csv") downloadCsv();
  });
  // Valor al focus de la coropleta (cursor o teclat).
  const showFocus = (e) => {
    const t = e.target.closest(".map-tile");
    const box = document.getElementById("map-focus");
    if (t && box) box.textContent = `${t.dataset.name} · ${layerFmt(state.mapLayer)(Number(t.dataset.val))}`;
  };
  app.addEventListener("pointerover", showFocus);
  app.addEventListener("focusin", showFocus);
}

function downloadCsv() {
  const rows = sortRows(filteredRows());
  const cols = ["nom_beneficiari", "clau_beneficiari", "nom_canonic", "codi_ine", "municipi", "comarca", "provincia", "codi_postal", "mesura", "fons", "exercici", "import_eur", "group_cif", "group_name", "estat_enllac", "cif", "clau_registral"];
  const escCsv = (v) => {
    const s = v == null ? "" : String(v);
    return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  };
  const csv = [cols.join(","), ...rows.map((r) => cols.map((c) => escCsv(r[c])).join(","))].join("\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = "ordit_ajudes_pac.csv";
  a.click();
  URL.revokeObjectURL(url);
}

/* ---------- Arrencada ---------- */
(async () => {
  try {
    const [marts, geo] = await Promise.all([loadMarts(), loadGeo(GEO_URL)]);
    state.rows = marts.rows;
    state.surf = buildSurf(marts.surfRows);
    state.useByIne = buildUse(marts.useRows);
    // Etiqueta representativa i enllac per clau canonica (constants per clau a tot el mart).
    for (const r of marts.rows) {
      state.canonLabel.set(r.clau_beneficiari, r.nom_canonic);
      if (r.cif) state.linkByClau.set(r.clau_beneficiari, { estat: r.estat_enllac, cif: r.cif, clauReg: r.clau_registral });
    }
    state.geo = geo;
    setupEvents();
    render();
  } catch (err) {
    document.getElementById("app").innerHTML = `<div class="ex-error">
      <p><strong>No s'ha pogut carregar l'explorador.</strong></p>
      <p class="mono">${esc(err.message || err)}</p>
      <p>Has publicat el Parquet? Executa <code>just publish</code> i torna a obrir amb <code>just serve</code>.</p>
    </div>`;
  }
})();
