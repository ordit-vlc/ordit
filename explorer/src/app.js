/* Explorador d'Ordit · ajudes de la PAC a persones juridiques de la Comunitat Valenciana.
   Tot client-side: DuckDB-WASM llig el Parquet del mart i la resta es filtra en memoria
   (el mart son ~12k files). Identificadors en angles ASCII; interficie en valencia. */

import * as duckdb from "https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@1.29.0/+esm";

// Ruta del Parquet publicat (relativa a /explorer/), servit com a fitxer estatic.
const PARQUET_URL = new URL("../data/dist/mart_ajudes_pac_juridiques.parquet", location.href).href;

// Procedencia, sempre visible (cap dada sense font).
const SOURCE = {
  font: "FEGA · Beneficiaris PAC",
  url: "https://www.fega.gob.es/es/datos-abiertos/consulta-de-beneficiarios-pac",
  data: "2026-06-02",
  llic: "CC BY 4.0",
  estat: "confirmat",
};

const COLUMNS = [
  { key: "nom_beneficiari", label: "Beneficiari", type: "text", strong: true },
  { key: "municipi", label: "Municipi", type: "text" },
  { key: "mesura", label: "Mesura", type: "text" },
  { key: "fons", label: "Fons", type: "text" },
  { key: "exercici", label: "Exercici", type: "num" },
  { key: "import_eur", label: "Import (€)", type: "num", strong: true },
];

const FACETS = [
  { key: "exercici", title: "Exercici", search: false },
  { key: "fons", title: "Fons", search: false },
  { key: "municipi", title: "Municipi", search: true },
  { key: "mesura", title: "Mesura", search: true },
];

const TABLE_LIMIT = 300; // files mostrades a la taula (l'agregat i els KPI usen tot el filtrat)

const eur = new Intl.NumberFormat("ca-ES", { maximumFractionDigits: 0 });
const eur2 = new Intl.NumberFormat("ca-ES", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtEur = (n) => eur2.format(n) + " €";
const fmtInt = (n) => eur.format(n);

const state = {
  rows: [],
  query: "",
  sel: { exercici: new Set(), fons: new Set(), municipi: new Set(), mesura: new Set() },
  facetSearch: { municipi: "", mesura: "" },
  sortKey: "import_eur",
  sortDir: "desc",
  view: "taula", // taula | grafic
  chartBy: "municipi", // municipi | beneficiari
  density: "compacte",
};

/* ---------- Carrega del mart amb DuckDB-WASM ---------- */
async function loadMart() {
  const bundle = await duckdb.selectBundle(duckdb.getJsDelivrBundles());
  const workerUrl = URL.createObjectURL(
    new Blob([`importScripts("${bundle.mainWorker}");`], { type: "text/javascript" }),
  );
  const worker = new Worker(workerUrl);
  const db = new duckdb.AsyncDuckDB(new duckdb.ConsoleLogger(), worker);
  await db.instantiate(bundle.mainModule, bundle.pthreadWorker);
  URL.revokeObjectURL(workerUrl);

  const resp = await fetch(PARQUET_URL);
  if (!resp.ok) throw new Error(`No s'ha pogut llegir el Parquet (${resp.status}).`);
  await db.registerFileBuffer("mart.parquet", new Uint8Array(await resp.arrayBuffer()));

  const conn = await db.connect();
  const res = await conn.query(
    `select nom_beneficiari, municipi, provincia, mesura,
            cast(import_eur as double) as import_eur, fons, exercici,
            group_cif, group_name
     from 'mart.parquet'`,
  );
  await conn.close();
  return res.toArray().map((r) => r.toJSON());
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
  const head = `<div class="facet-head"><span class="facet-title">${f.title}</span>
    <span class="mono">${sel.size ? sel.size + " sel." : counts.size}</span></div>`;
  const searchBox = f.search
    ? `<input class="input facet-search" data-facet="${f.key}" placeholder="filtra ${f.title.toLowerCase()}…"
        value="${esc(state.facetSearch[f.key])}" aria-label="Filtra ${f.title}" />`
    : "";
  const list = shown
    .map(
      ([v, n]) => `<label class="facet-opt">
        <input type="checkbox" data-facet="${f.key}" value="${esc(v)}" ${sel.has(v) ? "checked" : ""} />
        <span class="opt-label">${esc(v)}</span><span class="opt-count">${n}</span></label>`,
    )
    .join("");
  const more = opts.length > shown.length ? `<div class="facet-more mono">+${opts.length - shown.length} mes…</div>` : "";
  return `<div class="facet">${head}${searchBox}<div class="facet-list">${list}${more}</div></div>`;
}

function kpiHtml(rows) {
  const benef = new Set(rows.map((r) => r.nom_beneficiari)).size;
  const munis = new Set(rows.map((r) => r.municipi)).size;
  const total = rows.reduce((a, r) => a + r.import_eur, 0);
  return `<div class="ex-kpis">
    <div class="stat"><div class="stat-label">Beneficiaris</div><div class="stat-num tnum">${fmtInt(benef)}</div><div class="stat-sub">persones juridiques</div></div>
    <div class="stat"><div class="stat-label">Ajudes</div><div class="stat-num tnum">${fmtInt(rows.length)}</div><div class="stat-sub">files (beneficiari·municipi·fons·mesura)</div></div>
    <div class="stat"><div class="stat-label">Import · €</div><div class="stat-num tnum">${fmtInt(total)}</div><div class="stat-sub">contribucio europea</div></div>
    <div class="stat"><div class="stat-label">Municipis</div><div class="stat-num tnum">${fmtInt(munis)}</div><div class="stat-sub">de la Comunitat Valenciana</div></div>
  </div>`;
}

function chipsHtml() {
  const chips = [];
  for (const f of FACETS) {
    for (const v of state.sel[f.key]) {
      chips.push(`<span class="chip">${esc(v)}<button data-chip-facet="${f.key}" data-chip-val="${esc(v)}" aria-label="Lleva ${esc(v)}">✕</button></span>`);
    }
  }
  if (!chips.length) return "";
  return `<div class="cluster" style="margin-bottom:var(--s-4)">${chips.join("")}</div>`;
}

function tableHtml(rows) {
  const ind = (k) => (state.sortKey === k ? `<span class="sort-ind">${state.sortDir === "asc" ? "▲" : "▼"}</span>` : "");
  const max = Math.max(...rows.map((r) => Math.abs(r.import_eur)), 1);
  const head = COLUMNS.map(
    (c) => `<th class="${c.type === "num" ? "num " : ""}sortable" data-sort="${c.key}">${c.label} ${ind(c.key)}</th>`,
  ).join("");
  const shown = rows.slice(0, TABLE_LIMIT);
  const body =
    shown
      .map((r) => {
        const bar = `<div class="cellbar"><i style="width:${(Math.abs(r.import_eur) / max) * 100}%"></i></div>`;
        return `<tr>
        <td class="cell-strong">${esc(r.nom_beneficiari)}</td>
        <td>${esc(r.municipi)}</td>
        <td>${esc(r.mesura)}</td>
        <td><span class="badge">${esc(r.fons)}</span></td>
        <td class="num">${r.exercici}</td>
        <td class="num cell-strong">${fmtEur(r.import_eur)}${bar}</td>
      </tr>`;
      })
      .join("") ||
    `<tr><td colspan="${COLUMNS.length}" style="text-align:center;padding:var(--s-7);color:var(--ink-3)">Cap ajuda coincideix amb els filtres.</td></tr>`;
  const note =
    rows.length > TABLE_LIMIT
      ? `mostrant ${TABLE_LIMIT} de ${fmtInt(rows.length)} files (l'agregat i els KPI usen totes)`
      : `${fmtInt(rows.length)} files`;
  return `<div class="ex-densitat cluster" style="justify-content:flex-end;margin-bottom:var(--s-3)">
      <span class="mono">Densitat</span>
      <div class="seg">
        <button data-density="compacte" class="${state.density === "compacte" ? "active" : ""}" aria-pressed="${state.density === "compacte"}">Compacte</button>
        <button data-density="comode" class="${state.density === "comode" ? "active" : ""}" aria-pressed="${state.density === "comode"}">Comode</button>
      </div>
    </div>
    <div class="table-wrap"><table class="data${state.density === "compacte" ? " compact" : ""}">
      <thead><tr>${head}</tr></thead><tbody>${body}</tbody>
    </table></div>
    <div class="pager" style="margin-top:var(--s-4)"><span class="info">${note} · ordenat per ${esc(COLUMNS.find((c) => c.key === state.sortKey)?.label || state.sortKey)} (${state.sortDir})</span>${provHtml(false)}</div>`;
}

function chartHtml(rows) {
  const by = state.chartBy;
  const data = aggregate(rows, by === "municipi" ? "municipi" : "nom_beneficiari").slice(0, 15);
  const max = Math.max(...data.map((d) => Math.abs(d.v)), 1);
  const cats = ["--cat-1", "--cat-2", "--cat-3", "--cat-4", "--cat-5", "--cat-6"];
  const bars = data
    .map(
      (d, i) => `<div class="barrow" style="grid-template-columns:220px 1fr auto">
      <span class="bl" title="${esc(d.k)}">${esc(d.k)}</span>
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
  const rows = sortRows(filteredRows());
  const facets = FACETS.map(facetHtml).join("");
  const content =
    state.view === "taula" ? tableHtml(rows) : chartHtml(rows);
  document.getElementById("app").innerHTML = `
    <header class="ex-bar"><div class="ex-bar-inner">
      <a class="ordit-logo" href="#"><span class="ordit-mark">${MARK}</span><span class="ordit-word"><b>or</b>dit</span></a>
      <span class="badge" style="margin-left:.4rem">explorador</span>
      <div class="search" style="flex:1 1 320px;max-width:440px;margin-left:auto">
        <input class="input" id="q" value="${esc(state.query)}" placeholder="Cerca beneficiari o municipi…" aria-label="Cerca" />
      </div>
      <div class="cluster" style="gap:.5rem"><button class="btn btn-primary btn-sm" id="csv">Descarrega CSV</button></div>
    </div></header>
    <div class="ex-layout">
      <aside class="ex-aside">
        <div class="cluster" style="justify-content:space-between;margin-bottom:var(--s-3)">
          <span class="mono" style="color:var(--ink-2)">Filtres</span>
          <button class="btn btn-ghost btn-sm" id="clear">Neteja</button>
        </div>${facets}
      </aside>
      <main class="ex-main">
        ${kpiHtml(rows)}
        <div class="ex-controls">
          <div class="cluster"><span class="mono" style="margin-right:.2rem">Vista</span>
            <div class="seg">
              <button data-view="taula" class="${state.view === "taula" ? "active" : ""}" aria-pressed="${state.view === "taula"}">Taula</button>
              <button data-view="grafic" class="${state.view === "grafic" ? "active" : ""}" aria-pressed="${state.view === "grafic"}">Grafic</button>
            </div>
          </div>
          <div class="cluster" style="gap:.7rem">${provHtml(true)}<span class="status is-ok">Confirmat</span></div>
        </div>
        ${chipsHtml()}
        ${content}
      </main>
    </div>`;
}

/* ---------- Esdeveniments (delegacio) ---------- */
function setupEvents() {
  const app = document.getElementById("app");
  app.addEventListener("click", (e) => {
    const t = e.target.closest("[data-sort],[data-view],[data-chartby],[data-density],[data-chip-facet],#clear");
    if (!t) return;
    if (t.dataset.sort) {
      const k = t.dataset.sort;
      if (state.sortKey === k) state.sortDir = state.sortDir === "asc" ? "desc" : "asc";
      else {
        state.sortKey = k;
        state.sortDir = k === "import_eur" || k === "exercici" ? "desc" : "asc";
      }
    } else if (t.dataset.view) state.view = t.dataset.view;
    else if (t.dataset.chartby) state.chartBy = t.dataset.chartby;
    else if (t.dataset.density) state.density = t.dataset.density;
    else if (t.dataset.chipFacet) state.sel[t.dataset.chipFacet].delete(t.dataset.chipVal);
    else if (t.id === "clear") {
      for (const f of FACETS) state.sel[f.key].clear();
      state.query = "";
      state.facetSearch.municipi = "";
      state.facetSearch.mesura = "";
    }
    render();
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
}

function downloadCsv() {
  const rows = sortRows(filteredRows());
  const cols = ["nom_beneficiari", "municipi", "provincia", "mesura", "fons", "exercici", "import_eur", "group_cif", "group_name"];
  const escCsv = (v) => {
    const s = v == null ? "" : String(v);
    return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  };
  const csv = [cols.join(","), ...rows.map((r) => cols.map((c) => escCsv(r[c])).join(","))].join("\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = "ordit_ajudes_pac_juridiques.csv";
  a.click();
  URL.revokeObjectURL(url);
}

/* ---------- Arrencada ---------- */
(async () => {
  try {
    state.rows = await loadMart();
    setupEvents();
    render();
  } catch (err) {
    document.getElementById("app").innerHTML = `<div class="ex-error">
      <p><strong>No s'ha pogut carregar el mart.</strong></p>
      <p class="mono">${esc(err.message || err)}</p>
      <p>Has publicat el Parquet? Executa <code>just publish</code> i torna a obrir amb <code>just serve</code>.</p>
    </div>`;
  }
})();
