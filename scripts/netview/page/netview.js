'use strict';
/*
 * Network view: the page script.
 *
 * Every quantity is computed by the build step (scripts/netview/nv_build.py); this script selects and draws.
 * Sections: 1 decode, 2 model, 3 state and colours, 4 graph, 5 time bar and timeline, 6 small charts,
 * 7 detail panel, 8 summaries over the run, 9 legend and missing parts, 10 interaction and start.
 */

// ============================================================================================ 1. decode

function b64ToBytes(s) {
  if (Uint8Array.fromBase64) return Uint8Array.fromBase64(s);
  const bin = atob(s);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

/** The data block: {H: header, A: {name: typed array view}}. */
async function decodeBlock() {
  const el = document.getElementById('nv-data');
  let bytes = b64ToBytes(el.textContent.trim());
  el.textContent = '';
  if (el.dataset.encoding === 'gzip') {
    const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
    bytes = new Uint8Array(await new Response(stream).arrayBuffer());
  }
  const magic = String.fromCharCode(bytes[0], bytes[1], bytes[2], bytes[3]);
  if (magic !== 'NVB1') throw new Error('not a network view data block');
  const hlen = new DataView(bytes.buffer, bytes.byteOffset).getUint32(4, true);
  const H = JSON.parse(new TextDecoder().decode(bytes.subarray(8, 8 + hlen)));
  let base = 8 + hlen;
  base += (8 - base % 8) % 8;
  const A = {};
  for (const a of H.arrays) {
    const Ctor = window[a.type];
    A[a.name] = new Ctor(bytes.buffer, bytes.byteOffset + base + a.offset, a.length);
    A[a.name].shape = a.shape;
  }
  return { H, A };
}

// ============================================================================================ 2. model

const INT32_MIN = -2147483648;
const ST = {
  float: 0, not_candidate: 1, no_float: 2, window: 3, sigma: 4, fraction: 5, lattice: 6, persist: 7, odds: 8,
  cap: 9, wl_fraction: 10, code_event: 11, refused: 12, decided: 13, held: 14, would_hold: 15,
};
const M = {};

function buildModel(H, A) {
  M.H = H; M.A = A;
  M.nEp = H.n_ep; M.nSta = H.stations.length; M.nSat = H.sats.length; M.nNode = M.nSta + M.nSat;
  M.nBand = H.bands.length; M.nFam = H.families.length;
  M.names = H.stations.map(s => s.name).concat(H.sats);
  M.nodeIndex = new Map(M.names.map((n, i) => [n, i]));
  M.lat = Float64Array.from(H.stations, s => (s.lat == null ? NaN : s.lat));
  M.lon = Float64Array.from(H.stations, s => (s.lon == null ? NaN : s.lon));
  M.frac = H.frac_scale;
  M.step = M.nEp > 1 ? (A.t_ms[M.nEp - 1] - A.t_ms[0]) / (M.nEp - 1) : 30000;
  M.hasTree = !!A.tree_parent;
  M.hasLinks = !!A.link_fam && A.link_fam.length > 0;
  M.hasFixing = H.families.some(f => f.fixing);
  M.maxDepthCache = {};
  M.famEpCache = {};
  if (M.hasLinks) indexLinks();
  indexEvents();
  indexJumps();
}

function indexLinks() {
  const A = M.A, nl = A.link_fam.length;
  M.nLinks = nl;
  M.rowLink = new Int32Array(A.ce_ep.length);
  M.linkKey = new Map();
  M.famLinkFirst = new Int32Array(M.nFam).fill(-1);
  M.famLinkEnd = new Int32Array(M.nFam).fill(-1);
  for (let l = 0; l < nl; l++) {
    const s = A.link_start[l], c = A.link_count[l];
    M.rowLink.fill(l, s, s + c);
    const f = A.link_fam[l];
    M.linkKey.set(f + '|' + A.link_sta[l] + '|' + A.link_sat[l], l);
    if (M.famLinkFirst[f] < 0) M.famLinkFirst[f] = l;
    M.famLinkEnd[f] = l + 1;
  }
}

function indexEvents() {
  const A = M.A, n = A.ev_ep ? A.ev_ep.length : 0, nl = M.H.lanes.length;
  M.nEv = n;
  M.evOff = new Int32Array(M.nEp + 1);
  M.laneCount = Array.from({ length: nl }, () => new Int32Array(M.nEp));
  M.evBySta = Array.from({ length: M.nSta }, () => []);
  M.evBySat = Array.from({ length: M.nSat }, () => []);
  for (let i = 0; i < n; i++) {
    const e = A.ev_ep[i];
    M.evOff[e + 1]++;
    M.laneCount[A.ev_lane[i]][e]++;
    if (A.ev_sta[i] >= 0) M.evBySta[A.ev_sta[i]].push(i);
    if (A.ev_sat[i] >= 0) M.evBySat[A.ev_sat[i]].push(i);
  }
  for (let e = 0; e < M.nEp; e++) M.evOff[e + 1] += M.evOff[e];
}

function indexJumps() {
  M.jumps = new Map();
  const A = M.A;
  if (!A.jp_ep) return;
  for (let i = 0; i < A.jp_ep.length; i++) {
    const k = A.jp_fam[i] + '|' + A.jp_sat[i];
    if (!M.jumps.has(k)) M.jumps.set(k, []);
    M.jumps.get(k).push(i);
  }
}

// --- time

function gpsDate(e) {
  const ms = Date.UTC(1980, 0, 6) + (M.H.week0 * 604800000) + M.H.tow0_ms + M.A.t_ms[e];
  return new Date(ms);
}
function pad2(v) { return String(v).padStart(2, '0'); }
function clockOf(e) {
  const d = gpsDate(e);
  return pad2(d.getUTCHours()) + ':' + pad2(d.getUTCMinutes()) + ':' + pad2(d.getUTCSeconds());
}
function elapsedOf(e) {
  const m = Math.round(M.A.t_ms[e] / 60000);
  return Math.floor(m / 60) + ' h ' + pad2(m % 60) + ' min';
}
function dayOfYear(d) {
  return Math.floor((Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()) - Date.UTC(d.getUTCFullYear(), 0, 1)) / 864e5) + 1;
}
/** GPS time of epoch e in milliseconds since the GPS origin (the key two pages share when they are compared). */
function absMs(e) { return M.H.week0 * 604800000 + M.H.tow0_ms + M.A.t_ms[e]; }
/** The epoch nearest to an absolute GPS time, or -1 when it lies outside this run by more than one step. */
function epochAtMs(ms) {
  const rel = ms - M.H.week0 * 604800000 - M.H.tow0_ms, t = M.A.t_ms;
  if (rel < t[0] - M.step || rel > t[M.nEp - 1] + M.step) return -1;
  let lo = 0, hi = M.nEp - 1;
  while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (t[mid] <= rel) lo = mid; else hi = mid; }
  return Math.abs(t[hi] - rel) < Math.abs(t[lo] - rel) ? hi : lo;
}
/** Ticks at whole GPS hours (every second hour on long runs): [{e, label}]. */
function hourTicks() {
  if (M.ticks) return M.ticks;
  const H = 3600000, base = Date.UTC(1980, 0, 6) + M.H.week0 * 604800000 + M.H.tow0_ms;
  const t0 = base + M.A.t_ms[0], t1 = base + M.A.t_ms[M.nEp - 1];
  const step = (t1 - t0) / H > 14 ? 2 : 1;
  M.ticks = [];
  for (let h = Math.ceil(t0 / (step * H)) * step * H; h <= t1; h += step * H) {
    const e = epochAtMs(h - Date.UTC(1980, 0, 6));
    if (e >= 0) M.ticks.push({ e, label: pad2(new Date(h).getUTCHours()) + ':00' });
  }
  return M.ticks;
}
function durationText(nEpochs) {
  const m = Math.round(nEpochs * M.step / 60000);
  return m >= 60 ? Math.floor(m / 60) + ' h ' + pad2(m % 60) + ' min' : m + ' min';
}

// --- tree

function tIdx(b, n, e) { return (b * M.nNode + n) * M.nEp + e; }
function treeParent(b, n, e) { return M.hasTree && b >= 0 ? M.A.tree_parent[tIdx(b, n, e)] : -1; }
function treeDepth(b, n, e) { return M.hasTree && b >= 0 ? M.A.tree_depth[tIdx(b, n, e)] : -1; }
function treeTarget(b, n, e) {
  if (!M.hasTree || b < 0) return null;
  const v = M.A.tree_target[tIdx(b, n, e)];
  return v === INT32_MIN ? null : v;
}
function treeRow(b, n, e) { return M.hasTree && b >= 0 ? M.A.tree_row[tIdx(b, n, e)] : 0; }
/** Is the link (receiver node r, satellite node s) a tree link of signal b at epoch e? */
function isTreeLink(b, r, s, e) { return treeParent(b, s, e) === r || treeParent(b, r, e) === s; }
function maxDepth(b) {
  if (b < 0 || !M.hasTree) return 1;
  if (M.maxDepthCache[b] == null) {
    let m = 1;
    const base = b * M.nNode * M.nEp, d = M.A.tree_depth;
    for (let i = 0; i < M.nNode * M.nEp; i++) if (d[base + i] > m) m = d[base + i];
    M.maxDepthCache[b] = m;
  }
  return M.maxDepthCache[b];
}
/** Epochs at which the tree of signal b moved node n (a new parent, a return, a split or merge, a slipped link). */
function treeMoves(b, n) {
  const out = [];
  if (!M.hasTree || b < 0) return out;
  const kept = M.H.tree_rows.indexOf('kept'), root = M.H.tree_rows.indexOf('reference receiver');
  for (let e = 0; e < M.nEp; e++) {
    const r = treeRow(b, n, e);
    if (r !== 0 && r !== kept && r !== root) out.push(e);
  }
  return out;
}
/** What the tree did to node n at epoch e, in plain words, or '' when it kept it. */
function treeChangeText(b, n, e) {
  const r = treeRow(b, n, e), label = M.H.tree_rows[r] || '';
  return label === 'kept' || label === 'not in the tree' || label === 'reference receiver' ? '' : label;
}
/** The tree path from node n to its reference receiver (list of nodes), signal b, epoch e. */
function pathToRoot(b, n, e) {
  const out = [n];
  for (let k = 0; k < 64; k++) {
    const p = treeParent(b, out[out.length - 1], e);
    if (p < 0) break;
    out.push(p);
  }
  return out;
}

// --- links that are not tree links

function linkOf(f, sta, sat) {
  if (!M.hasLinks) return -1;
  const v = M.linkKey.get(f + '|' + sta + '|' + sat);
  return v == null ? -1 : v;
}
function linkRowAt(l, e) {
  const A = M.A;
  let lo = A.link_start[l], hi = lo + A.link_count[l] - 1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1, v = A.ce_ep[mid];
    if (v === e) return mid;
    if (v < e) lo = mid + 1; else hi = mid - 1;
  }
  return -1;
}
/** Rows of family f present at epoch e (a subarray of row indices). */
function famRowsAt(f, e) {
  if (!M.hasLinks || M.famLinkFirst[f] < 0) return new Int32Array(0);
  let c = M.famEpCache[f];
  if (!c) {
    const A = M.A, off = new Int32Array(M.nEp + 1);
    const r0 = A.link_start[M.famLinkFirst[f]];
    const lastL = M.famLinkEnd[f] - 1;
    const r1 = A.link_start[lastL] + A.link_count[lastL];
    for (let r = r0; r < r1; r++) off[A.ce_ep[r] + 1]++;
    for (let i = 0; i < M.nEp; i++) off[i + 1] += off[i];
    const rows = new Int32Array(r1 - r0), fill = off.slice(0, M.nEp);
    for (let r = r0; r < r1; r++) rows[fill[A.ce_ep[r]]++] = r;
    c = M.famEpCache[f] = { off, rows };
  }
  return c.rows.subarray(c.off[e], c.off[e + 1]);
}
function sigmaOf(code) {
  if (!code) return NaN;
  const [lo, hi] = M.H.sigma_code;
  return Math.pow(10, lo + code * (hi - lo) / 255);
}
/** Everything a row says: floats, distances from the whole numbers in use, sigmas, state, held integers. */
function rowInfo(r) {
  const A = M.A, f = M.frac;
  const wlInt = A.ce_wlint[r], nInt = A.ce_nint[r];
  const n1 = nInt + A.ce_dn1[r], wl = wlInt + A.ce_dwl[r];
  return {
    state: A.ce_state[r], ring: A.ce_ring[r],
    wlFloat: wlInt + A.ce_wlfrac[r] / f, nFloat: nInt + A.ce_nfrac[r] / f,
    wlDist: A.ce_wlfrac[r] / f - A.ce_dwl[r], nDist: A.ce_nfrac[r] / f - A.ce_dn1[r],
    sWl: sigmaOf(A.ce_swl[r]), sIf: sigmaOf(A.ce_sif[r]),
    n1, wl, n2: n1 - wl, res: A.ce_res[r],
  };
}
function stateKind(code) {
  if (code === ST.held) return 'held';
  if (code === ST.decided || code === ST.would_hold) return 'decided';
  if (code === ST.float) return 'float';
  return 'refused';
}

// --- products and receivers

function satSeries(name, sat, sig) {
  const A = M.A;
  if (name === 'clk') return A.sat_clk ? A.sat_clk.subarray(sat * M.nEp, (sat + 1) * M.nEp) : null;
  const tab = name === 'pb' ? M.H.phase_signals : M.H.code_signals;
  const arr = name === 'pb' ? A.sat_pb : A.sat_cb;
  const k = tab.indexOf(sig);
  if (!arr || k < 0) return null;
  const o = (k * M.nSat + sat) * M.nEp;
  return arr.subarray(o, o + M.nEp);
}
function satLevel(f, band, sat) {
  const a = M.A.sat_level;
  if (!a) return null;
  const o = ((f * 2 + band) * M.nSat + sat) * M.nEp;
  return a.subarray(o, o + M.nEp);
}
/** Elevation (degrees, NaN when not tracked) of satellite sat seen from receiver sta, over the run. */
function losElevation(sta, sat) {
  const a = M.A.los_el;
  if (!a) return null;
  const o = (sta * M.nSat + sat) * M.nEp, y = new Float32Array(M.nEp);
  let any = false;
  for (let e = 0; e < M.nEp; e++) { const v = a[o + e]; y[e] = v === 255 ? NaN : v; any = any || v !== 255; }
  return any ? y : null;
}
function rxSeries(name, sta, band) {
  const a = M.A[name];
  if (!a) return null;
  const o = (band == null ? sta : band * M.nSta + sta) * M.nEp;
  return a.subarray(o, o + M.nEp);
}

// ============================================================================================ 3. state and colours

const S = {
  ep: 0, fam: 0, bandSel: 0, layout: 'rings', showFloat: true, showHeld: true, showLabels: true,
  sel: null, hover: null, playing: false, speed: 5, showOther: false,
};
const C = {};
const COLOR_KEYS = ['bg', 'panel', 'ink', 'muted', 'line', 'soft', 'tree', 'held', 'decided', 'refused', 'float',
  'release', 'slip', 'gap', 'alarm', 'coderef', 'other', 'whole', 'iono', 'frac', 'sel', 'root', 'cursor', 'grid'];
const LANE_COLOR = { hold: 'held', release: 'release', tree: 'tree', slip: 'slip', gap: 'gap', alarm: 'alarm',
  coderef: 'coderef', other: 'other' };

function readColors() {
  const cs = getComputedStyle(document.documentElement);
  for (const k of COLOR_KEYS) C[k] = cs.getPropertyValue('--' + k).trim();
}
function rampColor(table, t) {
  if (!isFinite(t)) return C.soft;
  t = Math.max(0, Math.min(1, t));
  const x = t * (table.length - 1), i = Math.min(table.length - 2, Math.floor(x)), u = x - i;
  const c = [0, 1, 2].map(k => Math.round(255 * (table[i][k] * (1 - u) + table[i + 1][k] * u)));
  return 'rgb(' + c.join(',') + ')';
}
function viridis(t) { return rampColor(window.NV_ASSETS.colormaps.viridis, t); }
function vik(t) { return rampColor(window.NV_ASSETS.colormaps.vik, (t + 1) / 2); }
function withAlpha(color, a) {
  if (color.startsWith('#')) {
    const n = parseInt(color.slice(1), 16);
    return 'rgba(' + ((n >> 16) & 255) + ',' + ((n >> 8) & 255) + ',' + (n & 255) + ',' + a + ')';
  }
  if (color.startsWith('rgb(')) return color.replace('rgb(', 'rgba(').replace(')', ',' + a + ')');
  return color;
}
function laneColor(lane) { return C[LANE_COLOR[M.H.lanes[lane].key]] || C.other; }

function curFamily() {
  const f = M.H.families[S.fam];
  if (!f) return null;
  return { f, fi: S.fam, b: S.bandSel ? f.band2 : f.band1, bo: S.bandSel ? f.band1 : f.band2,
    sig: S.bandSel ? f.b2 : f.b1 };
}
function sysName(c) { return { G: 'GPS', E: 'Galileo', C: 'BeiDou', J: 'QZSS', R: 'GLONASS' }[c] || c; }
function famLabel(f) { return sysName(f.sys) + ' ' + f.b1 + ' + ' + f.b2; }
function shortSta(name) { return name.slice(0, 4); }
function esc(s) { return String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])); }
function fmt(v, d = 3) { return isFinite(v) ? v.toFixed(d) : 'n/a'; }
function fmtSigned(v, d = 3) { return isFinite(v) ? (v >= 0 ? '+' : '') + v.toFixed(d) : 'n/a'; }

// ============================================================================================ 4. graph

const G = { nodes: [], links: [], pos: null };

/** The family's links at epoch e: tree links of both signals and the links that are not tree links. */
function collectGraph(e) {
  const cf = curFamily();
  const out = { cf, present: new Uint8Array(M.nNode), depth: new Int8Array(M.nNode).fill(-1),
    root: new Int16Array(M.nNode).fill(-1), links: [], roots: [] };
  if (!cf) return out;
  const { b, bo, fi } = cf;
  const sys = cf.f.sys;
  const famNode = n => n < M.nSta || M.names[n][0] === sys;
  for (let n = 0; n < M.nNode; n++) {
    if (!famNode(n)) continue;
    const p = treeParent(b, n, e);
    if (p !== -1) { out.present[n] = 1; out.depth[n] = treeDepth(b, n, e); if (p === -2) out.roots.push(n); }
    if (treeParent(bo, n, e) !== -1) out.present[n] = 1;
  }
  // tree links of the drawn signal, then those of the other signal only
  for (let n = M.nSta; n < M.nNode; n++) {
    if (!famNode(n)) continue;
    for (const [band, kind] of [[b, 'tree'], [bo, 'treeOther']]) {
      const p = treeParent(band, n, e);
      if (p >= 0) addTreeLink(out, kind, band, p, n, e, b, bo);
    }
  }
  for (let r = 0; r < M.nSta; r++) {
    for (const [band, kind] of [[b, 'tree'], [bo, 'treeOther']]) {
      const p = treeParent(band, r, e);
      if (p >= 0) addTreeLink(out, kind, band, r, p, e, b, bo);
    }
  }
  for (const r of famRowsAt(fi, e)) {
    const l = M.rowLink[r];
    const sta = M.A.link_sta[l], sat = M.nSta + M.A.link_sat[l];
    out.present[sta] = 1; out.present[sat] = 1;
    out.links.push({ a: sta, s: sat, kind: stateKind(M.A.ce_state[r]), row: r, link: l });
  }
  // component of each node (its reference receiver in the drawn signal)
  for (let n = 0; n < M.nNode; n++) {
    if (out.depth[n] < 0) continue;
    const path = pathToRoot(b, n, e);
    out.root[n] = path[path.length - 1];
  }
  inwardCounts(out);
  return out;
}

function addTreeLink(out, kind, band, sta, sat, e, b, bo) {
  if (kind === 'treeOther' && isTreeLink(b, sta, sat, e)) return;
  const both = kind === 'tree' && isTreeLink(bo, sta, sat, e);
  out.links.push({ a: sta, s: sat, kind, both, band, row: -1, link: -1 });
}

/** Per node: links towards the reference (to nodes of fewer hops) and how many of them are whole numbers. */
function inwardCounts(gr) {
  gr.inTotal = new Int16Array(M.nNode);
  gr.inWhole = new Int16Array(M.nNode);
  const whole = k => k === 'tree' || k === 'held' || k === 'decided';
  for (const lk of gr.links) {
    for (const [n, m] of [[lk.a, lk.s], [lk.s, lk.a]]) {
      const dn = gr.depth[n], dm = gr.depth[m];
      if (dn < 0 || dm < 0 || dm >= dn) continue;
      gr.inTotal[n]++;
      if (whole(lk.kind)) gr.inWhole[n]++;
    }
  }
}

function bearing(lat1, lon1, lat2, lon2) {
  const r = Math.PI / 180, p1 = lat1 * r, p2 = lat2 * r, dl = (lon2 - lon1) * r;
  return Math.atan2(Math.sin(dl) * Math.cos(p2), Math.cos(p1) * Math.sin(p2) - Math.sin(p1) * Math.cos(p2) * Math.cos(dl));
}
function hashAngle(n) { return ((n * 2654435761) % 6283) / 1000; }

/** Spread sorted angles on a circle so that neighbours sit at least minSep apart (order kept). */
function spreadAngles(items, minSep) {
  const n = items.length;
  if (n < 2) return;
  items.sort((p, q) => p.ang - q.ang);
  minSep = Math.min(minSep, 2 * Math.PI / n * 0.92);
  for (let it = 0; it < 60; it++) {
    let moved = false;
    for (let i = 0; i < n; i++) {
      const j = (i + 1) % n;
      let gap = items[j].ang - items[i].ang;
      if (j === 0) gap += 2 * Math.PI;
      if (gap < minSep - 1e-9) {
        const d = (minSep - gap) / 2;
        items[i].ang -= d; items[j].ang += d; moved = true;
      }
    }
    if (!moved) break;
  }
}

function satCentroid(gr, s) {
  let x = 0, y = 0, z = 0, k = 0;
  for (const lk of gr.links) {
    if (lk.s !== s || !isFinite(M.lat[lk.a])) continue;
    const la = M.lat[lk.a] * Math.PI / 180, lo = M.lon[lk.a] * Math.PI / 180;
    x += Math.cos(la) * Math.cos(lo); y += Math.cos(la) * Math.sin(lo); z += Math.sin(la); k++;
  }
  if (!k) return null;
  return { lat: Math.atan2(z, Math.hypot(x, y)) * 180 / Math.PI, lon: Math.atan2(y, x) * 180 / Math.PI };
}

/**
 * The hops a ring picture shows for signal b: the depth that 99 % of the run's node-epochs do not exceed
 * (deeper nodes sit on its ring, labelled "or more"), so a rare deep excursion does not shrink every ring.
 */
function ringDepth(b) {
  if (b < 0 || !M.hasTree) return 1;
  M.ringDepthCache = M.ringDepthCache || {};
  if (M.ringDepthCache[b] == null) {
    const hist = new Int32Array(128), base = b * M.nNode * M.nEp, d = M.A.tree_depth;
    let n = 0;
    for (let i = 0; i < M.nNode * M.nEp; i++) { const v = d[base + i]; if (v > 0) { hist[v]++; n++; } }
    let acc = 0, k = 1;
    for (; k < 128; k++) { acc += hist[k]; if (acc >= 0.99 * n) break; }
    M.ringDepthCache[b] = Math.max(2, k);
  }
  return M.ringDepthCache[b];
}

/** Direction of every present node as seen from the reference receiver (radians from north). */
function nodeBearings(gr, main) {
  const rlat = main >= 0 && main < M.nSta ? M.lat[main] : NaN, rlon = main >= 0 && main < M.nSta ? M.lon[main] : NaN;
  const ang = new Float64Array(M.nNode).fill(NaN);
  for (let n = 0; n < M.nSta; n++) {
    if (!gr.present[n]) continue;
    ang[n] = isFinite(rlat) && isFinite(M.lat[n]) && n !== main ? bearing(rlat, rlon, M.lat[n], M.lon[n]) : hashAngle(n);
  }
  // a satellite looks the way of the receivers that see it
  const sx = new Float64Array(M.nNode), sy = new Float64Array(M.nNode);
  for (const lk of gr.links) {
    if (!isFinite(ang[lk.a]) || lk.a === main) continue;
    sx[lk.s] += Math.cos(ang[lk.a]); sy[lk.s] += Math.sin(ang[lk.a]);
  }
  for (let n = M.nSta; n < M.nNode; n++) if (gr.present[n]) ang[n] = (sx[n] || sy[n]) ? Math.atan2(sy[n], sx[n]) : hashAngle(n);
  return ang;
}

/**
 * Radial tree: the reference receiver at the centre, each node on the ring of its hops, and each subtree in a
 * wedge as wide as its number of leaves; children run clockwise in the order of their direction from the
 * reference receiver.  Tree links never cross.  Nodes off the main tree go on the outer ring.
 */
function layoutRings(gr, w, h) {
  const pos = new Array(M.nNode).fill(null);
  const cx = w / 2, cy = h / 2 + 6, R = Math.max(60, Math.min(w, h) / 2 - 30);
  const b = gr.cf ? gr.cf.b : -1;
  const Dh = ringDepth(b), D = Dh + 1;
  const size = new Map();
  for (let n = 0; n < M.nNode; n++) if (gr.root[n] >= 0) size.set(gr.root[n], (size.get(gr.root[n]) || 0) + 1);
  let main = -1, best = -1;
  for (const [rt, c] of size) if (c > best) { best = c; main = rt; }
  gr.mainRoot = main;
  const ang = nodeBearings(gr, main);
  const kids = Array.from({ length: M.nNode }, () => []);
  for (let n = 0; n < M.nNode; n++) {
    if (gr.root[n] !== main || n === main) continue;
    const p = treeParent(b, n, S.ep);
    if (p >= 0) kids[p].push(n);
  }
  const leaves = new Float64Array(M.nNode);
  const countLeaves = n => {
    let s = 0;
    for (const c of kids[n]) s += countLeaves(c);
    leaves[n] = Math.max(1, s);
    return leaves[n];
  };
  const placed = new Uint8Array(M.nNode);
  const place = (n, a0, a1) => {
    const a = (a0 + a1) / 2, d = Math.min(gr.depth[n], Dh), r = ringRadius(R, d, D);
    pos[n] = { x: cx + r * Math.sin(a), y: cy - r * Math.cos(a), ring: d, ang: a };
    placed[n] = 1;
    const ks = kids[n].slice().sort((p, q) => ang[p] - ang[q]);
    let t = a0;
    for (const c of ks) { const span = (a1 - a0) * leaves[c] / leaves[n]; place(c, t, t + span); t += span; }
  };
  if (main >= 0) {
    countLeaves(main);
    pos[main] = { x: cx, y: cy, ring: 0, ang: 0 };
    placed[main] = 1;
    const ks = kids[main].slice().sort((p, q) => ang[p] - ang[q]);
    let t = ks.length ? ang[ks[0]] - Math.PI * leaves[ks[0]] / leaves[main] : 0;
    for (const c of ks) { const span = 2 * Math.PI * leaves[c] / leaves[main]; place(c, t, t + span); t += span; }
  }
  const outer = [];
  for (let n = 0; n < M.nNode; n++) if (gr.present[n] && !placed[n]) outer.push({ n, ang: ang[n] });
  const ro = ringRadius(R, D, D);
  spreadAngles(outer, 15 / ro);
  for (const it of outer) pos[it.n] = { x: cx + ro * Math.sin(it.ang), y: cy - ro * Math.cos(it.ang), ring: D, ang: it.ang };
  G.ringGeom = { cx, cy, R, D, Dh, deeper: maxDepth(b) > Dh };
  return pos;
}

/** Radius of ring d (D = the outer ring): mildly compressed outward, where the deep rings hold few nodes. */
function ringRadius(R, d, D) { return R * Math.pow(d / D, 0.6); }

function mapRect(w, h) {
  const m = 14;
  let mw = w - 2 * m, mh = mw / 2;
  if (mh > h - 2 * m) { mh = h - 2 * m; mw = mh * 2; }
  return { x0: (w - mw) / 2, y0: (h - mh) / 2, w: mw, h: mh };
}
function mapXY(rc, lat, lon) { return { x: rc.x0 + (lon + 180) / 360 * rc.w, y: rc.y0 + (90 - lat) / 180 * rc.h }; }

function layoutMap(gr, w, h) {
  const rc = mapRect(w, h), pos = new Array(M.nNode).fill(null);
  for (let n = 0; n < M.nSta; n++) if (gr.present[n] && isFinite(M.lat[n])) pos[n] = mapXY(rc, M.lat[n], M.lon[n]);
  const sl = M.A.sat_lat, so = M.A.sat_lon;
  for (let n = M.nSta; n < M.nNode; n++) {
    if (!gr.present[n]) continue;
    const i = (n - M.nSta) * M.nEp + S.ep;
    const c = sl && isFinite(sl[i]) ? { lat: sl[i], lon: so[i] } : satCentroid(gr, n);
    if (c) pos[n] = mapXY(rc, c.lat, c.lon);
  }
  G.mapRect = rc;
  let main = -1, best = -1;
  const size = new Map();
  for (let n = 0; n < M.nNode; n++) if (gr.root[n] >= 0) size.set(gr.root[n], (size.get(gr.root[n]) || 0) + 1);
  for (const [rt, c] of size) if (c > best) { best = c; main = rt; }
  gr.mainRoot = main;
  return pos;
}

function fitCanvas(cv) {
  const dpr = window.devicePixelRatio || 1;
  const w = cv.clientWidth, h = cv.clientHeight;
  if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) {
    cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr);
  }
  const ctx = cv.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { ctx, w, h };
}

function releasesAt(e, fi) {
  const out = [];
  if (!M.nEv) return out;
  const A = M.A, rel = M.H.lanes.findIndex(l => l.key === 'release');
  const fam = M.H.families[fi];
  for (let i = M.evOff[e]; i < M.evOff[e + 1]; i++) {
    if (A.ev_lane[i] !== rel || A.ev_sta[i] < 0 || A.ev_sat[i] < 0) continue;
    if (M.H.sats[A.ev_sat[i]][0] !== fam.sys) continue;
    out.push({ a: A.ev_sta[i], s: M.nSta + A.ev_sat[i], cause: M.H.events.actions[A.ev_action[i]] });
  }
  return out;
}
function alarmNodesNear(e) {
  const set = new Set();
  if (!M.nEv) return set;
  const A = M.A, al = M.H.lanes.findIndex(l => l.key === 'alarm');
  for (let k = Math.max(0, e - 2); k <= e; k++) {
    for (let i = M.evOff[k]; i < M.evOff[k + 1]; i++) {
      if (A.ev_lane[i] !== al) continue;
      if (A.ev_sta[i] >= 0) set.add(A.ev_sta[i]);
      if (A.ev_sat[i] >= 0) set.add(M.nSta + A.ev_sat[i]);
    }
  }
  return set;
}

function drawGraph() {
  const cv = document.getElementById('graph');
  const { ctx, w, h } = fitCanvas(cv);
  if (!w || !h) return;
  ctx.clearRect(0, 0, w, h);
  G.nodes = []; G.links = [];
  if (!M.hasTree && !M.hasLinks) {
    ctx.fillStyle = C.muted; ctx.font = '14px system-ui, sans-serif'; ctx.textAlign = 'center';
    ctx.fillText('This run has no tree trace: the network cannot be drawn.', w / 2, h / 2 - 10);
    ctx.fillText('See the note above the network for the key that writes it.', w / 2, h / 2 + 12);
    return;
  }
  const gr = collectGraph(S.ep);
  const pos = S.layout === 'map' ? layoutMap(gr, w, h) : layoutRings(gr, w, h);
  G.gr = gr; G.pos = pos;
  if (S.layout === 'map') drawCoast(ctx); else drawRingGuides(ctx);
  const sel = S.sel;
  const selNodes = new Set();
  if (sel && (sel.kind === 'sta' || sel.kind === 'sat')) selNodes.add(sel.node);
  if (sel && sel.kind === 'link') { selNodes.add(sel.sta); selNodes.add(M.nSta + sel.sat); }
  const fade = sel && (sel.kind === 'sta' || sel.kind === 'sat');
  const order = { float: 0, refused: 1, treeOther: 2, held: 3, decided: 4, tree: 5 };
  const links = gr.links.slice().sort((p, q) => order[p.kind] - order[q.kind]);
  for (const lk of links) {
    const pa = pos[lk.a], ps = pos[lk.s];
    if (!pa || !ps) continue;
    if (!linkShown(lk)) continue;
    const touches = selNodes.has(lk.a) || selNodes.has(lk.s);
    const alpha = fade && !touches ? 0.12 : 1;
    styleLink(ctx, lk, alpha);
    ctx.beginPath(); ctx.moveTo(pa.x, pa.y); ctx.lineTo(ps.x, ps.y); ctx.stroke();
    ctx.setLineDash([]);
    G.links.push({ lk, x1: pa.x, y1: pa.y, x2: ps.x, y2: ps.y });
  }
  if (sel) drawSelection(ctx, gr, pos, sel);
  for (const rl of releasesAt(S.ep, S.fam)) {
    const pa = pos[rl.a], ps = pos[rl.s];
    if (!pa || !ps) continue;
    const mx = (pa.x + ps.x) / 2, my = (pa.y + ps.y) / 2;
    ctx.strokeStyle = C.release; ctx.lineWidth = 2.2;
    ctx.beginPath(); ctx.moveTo(mx - 5, my - 5); ctx.lineTo(mx + 5, my + 5); ctx.moveTo(mx + 5, my - 5); ctx.lineTo(mx - 5, my + 5); ctx.stroke();
  }
  const alarms = alarmNodesNear(S.ep);
  for (let n = 0; n < M.nNode; n++) {
    const p = pos[n];
    if (!p) continue;
    drawNode(ctx, gr, n, p, fade && !selNodes.has(n) && !linkedToSel(gr, n, selNodes), alarms.has(n));
    G.nodes.push({ n, x: p.x, y: p.y });
  }
  if (S.showLabels) drawLabels(ctx, gr, pos, fade, selNodes);
  updateGraphKey(gr);
}

/** The checkboxes: float links and held links can be hidden (links of the selected node always show). */
function linkShown(lk) {
  const sel = S.sel;
  if (sel && (sel.kind === 'sta' || sel.kind === 'sat') && (lk.a === sel.node || lk.s === sel.node)) return true;
  if (sel && sel.kind === 'link' && lk.a === sel.sta && lk.s === M.nSta + sel.sat) return true;
  if (lk.kind === 'float' || lk.kind === 'refused') return S.showFloat;
  if (lk.kind === 'held' || lk.kind === 'decided') return S.showHeld;
  return true;
}

function linkedToSel(gr, n, selNodes) {
  for (const lk of gr.links) if ((lk.a === n && selNodes.has(lk.s)) || (lk.s === n && selNodes.has(lk.a))) return true;
  return false;
}

function styleLink(ctx, lk, alpha) {
  let c = C.float, wd = 0.8, dash = [];
  switch (lk.kind) {
    case 'tree': c = C.tree; wd = 1.9; break;
    case 'treeOther': c = C.tree; wd = 1.1; dash = [5, 4]; break;
    case 'held': c = C.held; wd = 1.7; break;
    case 'decided': c = C.decided; wd = 2.6; break;
    case 'refused': c = C.refused; wd = 0.9; alpha *= 0.55; break;
    default: c = C.float; wd = 0.7; alpha *= 0.4;
  }
  ctx.strokeStyle = withAlpha(c, alpha);
  ctx.lineWidth = wd;
  ctx.setLineDash(dash);
}

function drawSelection(ctx, gr, pos, sel) {
  const cf = gr.cf;
  const paths = [];
  if (sel.kind === 'link') paths.push(pathToRoot(cf.b, sel.sta, S.ep), pathToRoot(cf.b, M.nSta + sel.sat, S.ep));
  if (sel.kind === 'sta' || sel.kind === 'sat') paths.push(pathToRoot(cf.b, sel.node, S.ep));
  ctx.strokeStyle = withAlpha(C.sel, 0.85); ctx.lineWidth = 5; ctx.lineCap = 'round';
  for (const p of paths) {
    ctx.beginPath();
    let started = false;
    for (const n of p) {
      const q = pos[n];
      if (!q) continue;
      if (!started) { ctx.moveTo(q.x, q.y); started = true; } else ctx.lineTo(q.x, q.y);
    }
    ctx.stroke();
  }
  if (sel.kind === 'link') {
    const pa = pos[sel.sta], ps = pos[M.nSta + sel.sat];
    if (pa && ps) {
      ctx.strokeStyle = C.sel; ctx.lineWidth = 7; ctx.globalAlpha = 0.55;
      ctx.beginPath(); ctx.moveTo(pa.x, pa.y); ctx.lineTo(ps.x, ps.y); ctx.stroke();
      ctx.globalAlpha = 1;
    }
  }
  ctx.lineCap = 'butt';
}

function drawNode(ctx, gr, n, p, faded, alarm) {
  const isSat = n >= M.nSta;
  const root = gr.depth[n] === 0;
  const share = gr.inTotal[n] ? gr.inWhole[n] / gr.inTotal[n] : NaN;
  const r = root ? 8 : 5.5;
  ctx.globalAlpha = faded ? 0.25 : 1;
  ctx.fillStyle = root ? C.root : (gr.inTotal[n] ? viridis(share) : C.panel);
  ctx.strokeStyle = gr.depth[n] < 0 ? C.muted : C.ink;
  ctx.lineWidth = 1.1;
  ctx.setLineDash(gr.depth[n] < 0 || (gr.mainRoot >= 0 && gr.root[n] !== gr.mainRoot) ? [2, 2] : []);
  ctx.beginPath();
  if (!isSat) ctx.arc(p.x, p.y, r, 0, 2 * Math.PI);
  else if (M.names[n][0] === 'E') { ctx.moveTo(p.x, p.y - r - 1); ctx.lineTo(p.x + r + 1, p.y); ctx.lineTo(p.x, p.y + r + 1); ctx.lineTo(p.x - r - 1, p.y); ctx.closePath(); }
  else ctx.rect(p.x - r, p.y - r, 2 * r, 2 * r);
  ctx.fill(); ctx.stroke();
  ctx.setLineDash([]);
  if (root) { ctx.beginPath(); ctx.arc(p.x, p.y, r + 3.5, 0, 2 * Math.PI); ctx.stroke(); }
  if (alarm) {
    ctx.strokeStyle = C.alarm; ctx.lineWidth = 2.2;
    ctx.beginPath(); ctx.arc(p.x, p.y, r + 5, 0, 2 * Math.PI); ctx.stroke();
  }
  if (S.hover && S.hover.kind === 'node' && S.hover.node === n) {
    ctx.strokeStyle = C.sel; ctx.lineWidth = 2.5;
    ctx.beginPath(); ctx.arc(p.x, p.y, r + 3, 0, 2 * Math.PI); ctx.stroke();
  }
  ctx.globalAlpha = 1;
}

function drawLabels(ctx, gr, pos, fade, selNodes) {
  ctx.font = '10.5px system-ui, sans-serif';
  ctx.textBaseline = 'middle';
  for (let n = 0; n < M.nNode; n++) {
    const p = pos[n];
    if (!p) continue;
    const label = n < M.nSta ? shortSta(M.names[n]) : M.names[n];
    ctx.globalAlpha = fade && !selNodes.has(n) ? 0.3 : 0.9;
    ctx.fillStyle = n < M.nSta ? C.muted : C.ink;
    let dx = 9, dy = 0;
    if (S.layout !== 'map' && p.ring > 0) {
      const ux = Math.sin(p.ang), uy = -Math.cos(p.ang);
      dx = ux * 11; dy = uy * 11;
      ctx.textAlign = ux > 0.3 ? 'left' : ux < -0.3 ? 'right' : 'center';
    } else ctx.textAlign = 'left';
    if (n === gr.mainRoot && S.layout !== 'map') { dx = 0; dy = 20; ctx.textAlign = 'center'; ctx.fillStyle = C.ink; }
    ctx.fillText(n === gr.mainRoot ? M.names[n] : label, p.x + dx, p.y + dy);
  }
  ctx.globalAlpha = 1;
}

function drawRingGuides(ctx) {
  const g = G.ringGeom;
  if (!g) return;
  ctx.strokeStyle = C.grid; ctx.lineWidth = 1; ctx.fillStyle = C.muted;
  ctx.font = '10px system-ui, sans-serif'; ctx.textAlign = 'left'; ctx.textBaseline = 'bottom';
  for (let d = 1; d <= g.D; d++) {
    const r = ringRadius(g.R, d, g.D);
    ctx.setLineDash(d === g.D ? [3, 4] : []);
    ctx.beginPath(); ctx.arc(g.cx, g.cy, r, 0, 2 * Math.PI); ctx.stroke();
    const label = d === g.D ? 'off the main tree' : d + (d === 1 ? ' hop' : ' hops') + (d === g.Dh && g.deeper ? ' or more' : '');
    ctx.fillText(label, g.cx + 3, g.cy - r - 1);
  }
  ctx.setLineDash([]);
}

function drawCoast(ctx) {
  const rc = G.mapRect, cl = window.NV_ASSETS.coastline;
  ctx.fillStyle = C.soft; ctx.fillRect(rc.x0, rc.y0, rc.w, rc.h);
  if (!cl) return;
  ctx.strokeStyle = C.line; ctx.lineWidth = 0.8; ctx.beginPath();
  let pen = false;
  for (let i = 0; i < cl.lon.length; i++) {
    if (cl.lon[i] == null) { pen = false; continue; }
    const p = mapXY(rc, cl.lat[i], cl.lon[i]);
    if (!pen) { ctx.moveTo(p.x, p.y); pen = true; } else ctx.lineTo(p.x, p.y);
  }
  ctx.stroke();
}

function updateGraphKey(gr) {
  const el = document.getElementById('graph-key');
  const cf = gr.cf;
  if (!cf) { el.innerHTML = ''; return; }
  const counts = { tree: 0, treeOther: 0, held: 0, decided: 0, refused: 0, float: 0 };
  for (const lk of gr.links) counts[lk.kind]++;
  const ramp = [0, 0.25, 0.5, 0.75, 1].map(viridis).join(',');
  let html = '<div><span class="sw" style="border-color:' + C.tree + '"></span>tree link of ' + esc(cf.sig) + ' (' + counts.tree + ')</div>' +
    '<div><span class="sw" style="border-color:' + C.tree + ';border-top-style:dashed"></span>tree link of the other signal only (' + counts.treeOther + ')</div>';
  if (cf.f.fixing) {
    html += '<div><span class="sw" style="border-color:' + C.held + '"></span>held at whole numbers (' + counts.held + ')' +
      (counts.decided ? ', decided now (' + counts.decided + ')' : '') + '</div>' +
      '<div><span class="sw" style="border-color:' + C.refused + '"></span>float, not yet held (' + counts.refused + ')</div>';
  } else {
    html += '<div><span class="sw" style="border-color:' + C.float + '"></span>float, no fixing on these signals (' + counts.float + ')</div>';
  }
  html += '<div>node colour: share of its links towards the reference that are whole numbers <span class="bar" style="background:linear-gradient(90deg,' + ramp + ')"></span>0 to 1</div>' +
    '<div>&#9675; receiver &nbsp; &#9633; GPS &nbsp; &#9671; Galileo &nbsp; red ring: alarm in the last minute &nbsp; &#10005;: released now</div>';
  el.innerHTML = html;
}

function hitTest(x, y) {
  let best = null, bd = 10;
  for (const nd of G.nodes) {
    const d = Math.hypot(nd.x - x, nd.y - y);
    if (d < bd) { bd = d; best = { kind: 'node', node: nd.n }; }
  }
  if (best) return best;
  bd = 4.5;
  for (const g of G.links) {
    const d = segDist(x, y, g.x1, g.y1, g.x2, g.y2);
    if (d < bd) { bd = d; best = { kind: 'link', lk: g.lk }; }
  }
  return best;
}
function segDist(px, py, x1, y1, x2, y2) {
  const dx = x2 - x1, dy = y2 - y1, L = dx * dx + dy * dy;
  let t = L ? ((px - x1) * dx + (py - y1) * dy) / L : 0;
  t = Math.max(0, Math.min(1, t));
  return Math.hypot(px - x1 - t * dx, py - y1 - t * dy);
}

// ============================================================================================ 5. time bar and timeline

const TL = { labelW: 128, laneH: 14, top: 4, cache: null };

function timelineLanes() {
  const lanes = M.H.lanes.map((l, i) => ({ label: l.label, lane: i, color: laneColor(i), counts: M.laneCount[i] }));
  const sel = selectionEvents();
  if (sel) lanes.unshift({ label: 'Selected', lane: -1, color: C.sel, counts: sel.counts, selected: true });
  return lanes;
}

function drawTimeline() {
  const cv = document.getElementById('timeline');
  const lanes = timelineLanes();
  const hNeeded = TL.top + lanes.length * TL.laneH + 38;
  if (Math.abs(cv.clientHeight - hNeeded) > 1) {
    cv.style.height = hNeeded + 'px';         // a lane came or went: the network area below takes the difference
    if (G.gr) { fitMain(); drawGraph(); }
  }
  const { ctx, w, h } = fitCanvas(cv);
  if (!w || !h) return;                       // not laid out yet (a background tab); the resize handler redraws
  const key = [w, h, S.fam, selKey(S.sel), lanes.length].join('|');
  if (!TL.cache || TL.cache.key !== key) TL.cache = { key, img: renderTimelineStatic(lanes, w, h) };
  ctx.clearRect(0, 0, w, h);
  ctx.drawImage(TL.cache.img, 0, 0, w, h);
  const x = tlX(S.ep, w);
  ctx.strokeStyle = C.cursor; ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
}
function tlX(e, w) { return TL.labelW + (M.nEp > 1 ? e / (M.nEp - 1) : 0) * (w - TL.labelW - 8); }
function tlEp(x, w) { return Math.round(Math.max(0, Math.min(1, (x - TL.labelW) / (w - TL.labelW - 8))) * (M.nEp - 1)); }

function renderTimelineStatic(lanes, w, h) {
  const dpr = window.devicePixelRatio || 1;
  const off = document.createElement('canvas');
  off.width = Math.round(w * dpr); off.height = Math.round(h * dpr);
  const ctx = off.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.font = '11px system-ui, sans-serif'; ctx.textBaseline = 'middle';
  lanes.forEach((ln, k) => {
    const y0 = TL.top + k * TL.laneH;
    ctx.fillStyle = k % 2 ? C.panel : C.soft;
    ctx.fillRect(TL.labelW, y0, w - TL.labelW - 8, TL.laneH);
    ctx.fillStyle = C.ink; ctx.textAlign = 'right';
    let total = 0, max = 0;
    for (let e = 0; e < M.nEp; e++) { total += ln.counts[e]; if (ln.counts[e] > max) max = ln.counts[e]; }
    ctx.fillText(ln.label + ' ' + total, TL.labelW - 6, y0 + TL.laneH / 2);
    if (!max) return;
    ctx.fillStyle = ln.color;
    const lm = Math.log1p(max);
    for (let e = 0; e < M.nEp; e++) {
      const c = ln.counts[e];
      if (!c) continue;
      const hh = Math.max(3, (TL.laneH - 2) * Math.log1p(c) / lm);
      const x = tlX(e, w);
      ctx.fillRect(x - 0.75, y0 + TL.laneH - 1 - hh, 1.5, hh);
    }
  });
  const yAx = TL.top + lanes.length * TL.laneH;
  drawHeldShareStrip(ctx, w, yAx + 2, 18);
  ctx.fillStyle = C.muted; ctx.textAlign = 'center'; ctx.textBaseline = 'top';
  for (const tk of hourTicks()) {
    const x = tlX(tk.e, w);
    ctx.fillText(tk.label, x, yAx + 22);
    ctx.fillStyle = C.line; ctx.fillRect(x, TL.top, 1, lanes.length * TL.laneH); ctx.fillStyle = C.muted;
  }
  return off;
}

function drawHeldShareStrip(ctx, w, y0, hh) {
  const cf = curFamily();
  ctx.fillStyle = C.muted; ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
  ctx.font = '11px system-ui, sans-serif';
  if (!cf || !M.A.sum_links) return;
  const nf = M.nFam, ne = M.nEp, sl = M.A.sum_links;
  const label = cf.f.fixing ? 'Held share' : 'Links (count)';
  ctx.fillText(label, TL.labelW - 6, y0 + hh / 2);
  ctx.fillStyle = C.soft; ctx.fillRect(TL.labelW, y0, w - TL.labelW - 8, hh);
  let max = 1;
  if (!cf.f.fixing) for (let e = 0; e < ne; e++) max = Math.max(max, sl[cf.fi * ne + e]);
  ctx.fillStyle = withAlpha(cf.f.fixing ? C.held : C.float, 0.75);
  for (let e = 0; e < ne; e++) {
    const n = sl[cf.fi * ne + e], held = sl[(nf + cf.fi) * ne + e];
    const v = cf.f.fixing ? (n ? held / n : 0) : n / max;
    if (!v) continue;
    const x = tlX(e, w);
    ctx.fillRect(x - 0.75, y0 + hh * (1 - v), 1.6, hh * v);
  }
}

function selKey(sel) {
  if (!sel) return '';
  if (sel.kind === 'link') return 'link:' + sel.sta + ':' + sel.sat;
  if (sel.kind === 'events') return 'events:' + sel.ep + ':' + sel.lane;
  return sel.kind + ':' + sel.node;
}

/** Events of the selected link or node: per-epoch counts and the event indices. */
function selectionEvents() {
  const sel = S.sel;
  if (!sel || !M.nEv) return null;
  if (sel._ev) return sel._ev;
  let idx = [];
  const A = M.A;
  if (sel.kind === 'link') idx = M.evBySta[sel.sta].filter(i => A.ev_sat[i] === sel.sat);
  else if (sel.kind === 'sta') idx = M.evBySta[sel.node];
  else if (sel.kind === 'sat') idx = M.evBySat[sel.node - M.nSta];
  const counts = new Int32Array(M.nEp);
  for (const i of idx) counts[A.ev_ep[i]]++;
  sel._ev = { idx, counts };
  return sel._ev;
}

function updateTimeLabel() {
  document.getElementById('time-label').textContent =
    clockOf(S.ep) + ' GPS time, ' + elapsedOf(S.ep) + ' into the run (epoch ' + (S.ep + 1) + ' of ' + M.nEp + ')';
}

// ============================================================================================ 6. small charts

/**
 * A chart over the run's epochs on a canvas, its static part cached.  spec: {series: [{y, color, width, dash,
 * step}], bands: [{lo, hi, color}], hlines: [{y, color, dash}], dots: [{e, y, color, r}], ticks: [{e, color}],
 * strip: {codes, colors}, bars: [{e0, e1, stack: [{v, color}]}], yRange, symmetric, yFmt, title}.
 */
const CHARTS = [];
function makeChart(canvas, spec) {
  const ch = { cv: canvas, spec, img: null, key: '' };
  canvas.addEventListener('click', ev => {
    const r = canvas.getBoundingClientRect();
    setEp(chartEp(ch, ev.clientX - r.left));
  });
  canvas.addEventListener('mousemove', ev => {
    const r = canvas.getBoundingClientRect();
    const e = chartEp(ch, ev.clientX - r.left);
    canvas.title = clockOf(e) + (spec.valueAt ? '  ' + spec.valueAt(e) : '');
  });
  CHARTS.push(ch);
  drawChart(ch);
  return ch;
}
function chartBox(w, h, spec) {
  return { l: 50, r: 8, t: spec.title ? 15 : 5, b: spec.noAxis ? 4 : 15, w, h };
}
function chartX(bx, e) { return bx.l + (M.nEp > 1 ? e / (M.nEp - 1) : 0) * (bx.w - bx.l - bx.r); }
function chartEp(ch, x) {
  const bx = chartBox(ch.cv.clientWidth, ch.cv.clientHeight, ch.spec);
  return Math.round(Math.max(0, Math.min(1, (x - bx.l) / (bx.w - bx.l - bx.r))) * (M.nEp - 1));
}
function drawChart(ch) {
  if (!ch.cv.isConnected) return;
  const { ctx, w, h } = fitCanvas(ch.cv);
  if (!w || !h) return;
  const key = w + 'x' + h;
  if (!ch.img || ch.key !== key) { ch.img = renderChartStatic(ch.spec, w, h); ch.key = key; }
  ctx.clearRect(0, 0, w, h);
  ctx.drawImage(ch.img, 0, 0, w, h);
  const bx = chartBox(w, h, ch.spec), x = chartX(bx, S.ep);
  ctx.strokeStyle = C.cursor; ctx.lineWidth = 1.2;
  ctx.beginPath(); ctx.moveTo(x, bx.t); ctx.lineTo(x, h - bx.b); ctx.stroke();
}
function drawAllCharts() {
  for (let i = CHARTS.length - 1; i >= 0; i--) {
    if (!CHARTS[i].cv.isConnected) CHARTS.splice(i, 1); else drawChart(CHARTS[i]);
  }
}
function niceTicks(lo, hi, n) {
  const span = hi - lo;
  if (!(span > 0)) return [lo];
  const raw = span / n, mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const st = [1, 2, 2.5, 5, 10].map(m => m * mag).find(s => s >= raw) || 10 * mag;
  const out = [];
  for (let v = Math.ceil(lo / st) * st; v <= hi + 1e-12; v += st) out.push(Math.abs(v) < 1e-12 ? 0 : v);
  return out;
}
/** y range from the 1st to the 99th percentile of the series (a start-up transient does not flatten the rest). */
function robustRange(spec) {
  const v = [];
  for (const s of spec.series || []) for (let e = 0; e < s.y.length; e++) if (isFinite(s.y[e])) v.push(s.y[e]);
  if (v.length < 20) return null;
  v.sort((p, q) => p - q);
  const lo = v[Math.floor(0.01 * (v.length - 1))], hi = v[Math.ceil(0.99 * (v.length - 1))];
  const pad = Math.max((hi - lo) * 0.12, Math.abs(hi) * 1e-6, 1e-6);
  return [lo - pad, hi + pad];
}

function seriesRange(spec) {
  if (spec.robust) { const r = robustRange(spec); if (r) return r; }
  let lo = Infinity, hi = -Infinity;
  const take = v => { if (isFinite(v)) { if (v < lo) lo = v; if (v > hi) hi = v; } };
  for (const s of spec.series || []) for (let e = 0; e < s.y.length; e++) take(s.y[e]);
  for (const b of spec.bands || []) for (let e = 0; e < b.lo.length; e++) { take(b.lo[e]); take(b.hi[e]); }
  for (const d of spec.dots || []) take(d.y);
  for (const b of spec.bars || []) { let t = 0; for (const s of b.stack) t += s.v; take(t); take(0); }
  for (const l of spec.hlines || []) if (l.inRange) take(l.y);
  if (!isFinite(lo)) return [0, 1];
  if (spec.symmetric) { const m = Math.max(Math.abs(lo), Math.abs(hi), spec.minHalf || 0); return [-m * 1.08, m * 1.08]; }
  if (spec.zeroBased) lo = Math.min(lo, 0);
  if (hi - lo < (spec.minSpan || 1e-9)) { const c = (hi + lo) / 2, s = (spec.minSpan || 1) / 2; lo = c - s; hi = c + s; }
  const pad = (hi - lo) * 0.07;
  return [spec.zeroBased && lo === 0 ? 0 : lo - pad, hi + pad];
}
function renderChartStatic(spec, w, h) {
  const dpr = window.devicePixelRatio || 1;
  const off = document.createElement('canvas');
  off.width = Math.round(w * dpr); off.height = Math.round(h * dpr);
  const ctx = off.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const bx = chartBox(w, h, spec);
  const [y0, y1] = spec.yRange || seriesRange(spec);
  const Y = v => bx.t + (1 - (v - y0) / (y1 - y0)) * (h - bx.t - bx.b);
  const X = e => chartX(bx, e);
  ctx.font = '10.5px system-ui, sans-serif';
  if (spec.title) { ctx.fillStyle = C.ink; ctx.textAlign = 'left'; ctx.textBaseline = 'top'; ctx.fillText(spec.title, 2, 1); }
  ctx.fillStyle = C.panel; ctx.fillRect(bx.l, bx.t, w - bx.l - bx.r, h - bx.t - bx.b);
  // grid and y ticks
  if (!spec.strip) {
    ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
    for (const v of niceTicks(y0, y1, spec.nTicks || 3)) {
      const y = Y(v);
      ctx.strokeStyle = C.grid; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(bx.l, y); ctx.lineTo(w - bx.r, y); ctx.stroke();
      ctx.fillStyle = C.muted; ctx.fillText((spec.yFmt || shortNum)(v), bx.l - 4, y);
    }
  }
  // x ticks (hours)
  if (!spec.noAxis) {
    ctx.textAlign = 'center'; ctx.textBaseline = 'top'; ctx.fillStyle = C.muted;
    const ticks = hourTicks(), every = ticks.length > 8 ? 2 : 1;
    ticks.forEach((tk, i) => { if (i % every === 0) ctx.fillText(tk.label, X(tk.e), h - bx.b + 2); });
  }
  if (spec.strip) {
    const { codes, colors } = spec.strip;
    for (let e = 0; e < M.nEp; e++) {
      const c = colors[codes[e]];
      if (!c) continue;
      ctx.fillStyle = c;
      ctx.fillRect(X(e) - 0.5, bx.t + 2, Math.max(1, X(e + 1) - X(e)) + 0.5, h - bx.t - bx.b - 4);
    }
  }
  for (const b of spec.bars || []) {
    let acc = 0;
    const xa = X(b.e0) + 1, xb = X(b.e1) - 1;
    for (const s of b.stack) {
      if (!(s.v > 0)) continue;
      ctx.fillStyle = s.color;
      ctx.fillRect(xa, Y(acc + s.v), Math.max(1, xb - xa), Y(acc) - Y(acc + s.v));
      acc += s.v;
    }
    if (b.label) {
      ctx.fillStyle = C.muted; ctx.textAlign = 'center'; ctx.textBaseline = 'bottom'; ctx.font = '9px system-ui, sans-serif';
      ctx.fillText(b.label, (xa + xb) / 2, Y(acc) - 1);
      ctx.font = '10.5px system-ui, sans-serif';
    }
  }
  for (const b of spec.bands || []) {
    ctx.fillStyle = b.color;
    for (let e = 0; e < M.nEp; e++) {
      const lo = b.lo[e], hi = b.hi[e];
      if (!isFinite(lo) || !isFinite(hi)) continue;
      const ya = Y(Math.min(y1, hi)), yb = Y(Math.max(y0, lo));
      ctx.fillRect(X(e) - 0.6, ya, Math.max(1.2, X(e + 1) - X(e)), yb - ya);
    }
  }
  for (const l of spec.hlines || []) {
    if (l.y < y0 || l.y > y1) continue;
    ctx.strokeStyle = l.color || C.muted; ctx.lineWidth = 1; ctx.setLineDash(l.dash || [4, 3]);
    ctx.beginPath(); ctx.moveTo(bx.l, Y(l.y)); ctx.lineTo(w - bx.r, Y(l.y)); ctx.stroke(); ctx.setLineDash([]);
  }
  ctx.save();
  ctx.beginPath(); ctx.rect(bx.l, bx.t, w - bx.l - bx.r, h - bx.t - bx.b); ctx.clip();
  for (const s of spec.series || []) {
    ctx.strokeStyle = s.color; ctx.lineWidth = s.width || 1.3; ctx.setLineDash(s.dash || []);
    ctx.beginPath();
    let pen = false, prevY = 0;
    for (let e = 0; e < s.y.length; e++) {
      const v = s.y[e];
      if (!isFinite(v)) { pen = false; continue; }
      const x = X(e), y = Y(v);
      if (!pen) { ctx.moveTo(x, y); pen = true; }
      else if (s.step) { ctx.lineTo(x, prevY); ctx.lineTo(x, y); }
      else ctx.lineTo(x, y);
      prevY = y;
    }
    ctx.stroke(); ctx.setLineDash([]);
  }
  for (const d of spec.dots || []) {
    if (!isFinite(d.y)) continue;
    ctx.fillStyle = d.color; ctx.beginPath(); ctx.arc(X(d.e), Y(Math.max(y0, Math.min(y1, d.y))), d.r || 3, 0, 2 * Math.PI); ctx.fill();
  }
  ctx.restore();
  for (const t of spec.ticks || []) {
    ctx.fillStyle = t.color; ctx.fillRect(X(t.e) - 1, bx.t, 2, 6);
  }
  ctx.strokeStyle = C.line; ctx.lineWidth = 1; ctx.strokeRect(bx.l + 0.5, bx.t + 0.5, w - bx.l - bx.r - 1, h - bx.t - bx.b - 1);
  if (spec.empty) {
    ctx.fillStyle = C.muted; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText(spec.empty, (bx.l + w - bx.r) / 2, (bx.t + h - bx.b) / 2);
  }
  return off;
}
function shortNum(v) {
  const a = Math.abs(v);
  if (a === 0) return '0';
  if (a >= 1000) return v.toFixed(0);
  if (a >= 10) return v.toFixed(a >= 100 ? 0 : 1);
  if (a >= 1) return v.toFixed(2).replace(/0$/, '');
  return v.toPrecision(2);
}
function chartEl(parent, title, cls, keyItems) {
  const h3 = document.createElement('h3');
  h3.textContent = title;
  parent.appendChild(h3);
  const cv = document.createElement('canvas');
  cv.className = 'chart' + (cls ? ' ' + cls : '');
  parent.appendChild(cv);
  if (keyItems && keyItems.length) {
    const k = document.createElement('div');
    k.className = 'chart-key';
    k.innerHTML = keyItems.map(([c, t]) => '<span><i style="background:' + c + '"></i>' + esc(t) + '</span>').join('');
    parent.appendChild(k);
  }
  return cv;
}
function hint(parent, html) {
  const p = document.createElement('div');
  p.className = 'hint';
  p.innerHTML = html;
  parent.appendChild(p);
  return p;
}

// ============================================================================================ 7. detail panel

const EVENT_TEXT = {
  'RINGFIX/hold': 'whole numbers decided (held from the next epoch)',
  'RINGFIX/release': 'released',
  'RINGFIX/to_tree': 'became a tree link',
  'RINGFIX/reattach': 'the tree re-formed through this held link',
  'CHAIN/rehost': 'tree re-formed: a node moved to a new parent',
  'CHAIN/cut_release': 'tree cut: the moved side lets go of its links',
  'CHAIN/returning': 'a node returned to the tree',
  'CHAIN/split': 'the tree split in two',
  'CHAIN/merge': 'two trees merged',
  'CHAIN/slip_deseat': 'a tree link slipped and the node moved',
  'CHAIN/kept': 'tree link kept through an event',
  'CHAIN/declared_keys': 'tree bookkeeping after a move',
  'PHASE_DATUM/eq34_reattach': 'receiver re-attached to a new tree parent',
  'PHASE_DATUM/eq34_reref': 'phase reference re-realized',
  'T0_gap/arc_resume': 'tracking resumed after a gap',
  'T0_gap/sig_resume': 'signal resumed after a gap',
  'T0_gap/reentry_relevel': 'float re-levelled at a return',
  'SIGNAL/reentry': 'satellite back after a short gap',
  'SIGNAL/band_lost': 'a signal lost',
  'SIGNAL/band_regain': 'a signal regained',
  'READMIT/readmit': 'satellite readmitted after a long gap',
  'T0_mw_detect/lli_slip': 'slip: loss of lock reported by the receiver',
  'T0_mw_detect/mw_wl_slip': 'slip: wide-lane (Melbourne-Wubbena) jump',
  'T1_gf_jump/gf_jump': 'slip: geometry-free jump',
  'T1_if_slip/if_slip': 'slip: ionosphere-free time-difference test',
  'T0_windup/wu_restart': 'wind-up restarted',
  'RAIM/residual_alarm': 'alarm: post-fit residual too large',
  'T4_prior/prior_arc': 'alarm: a carried float re-opened',
  'T4_attrib/attrib_arc': 'alarm: a float re-opened by attribution',
  'GROSSLOS/gross_los_declare': 'alarm: gross error on this line of sight',
  'GROSSLOS/gross_los_clear': 'gross error cleared',
  'CLK_ANCHOR/cta_decouple': 'alarm: satellite clock left its anchor',
  'CLK_ANCHOR/cta_recouple': 'satellite clock back on its anchor',
  'CB_DATUM/reseed_disc_landed': 'code reference re-seeded',
  'CB_DATUM/family_birth_prior': 'code reference: new code signal of a satellite',
  'CLK_BASIS/reselect': 'the clock moved to another code reference',
  'ZWD/slip_latch': 'wet delay carry reset by a slip',
  'ZWD/recouple': 'wet delay carry resumed',
  'BLOCKBAARDA/block_outlier': 'outlier test of a receiver-satellite block',
  'MDB/mdb_exceedance': 'smallest detectable error above its bound',
  'CONGRUENCE/coordinate_offset': 'coordinate offset test',
};
const RELEASE_TEXT = {
  slip: 'a slip on either signal', refloat: 'its float re-opened by another check', gap: 'the link absent too long',
  chain: 'the tree changed around it', monitor: 'its residual stayed above 3 cm',
};
function eventText(i) {
  const A = M.A, E = M.H.events;
  const tier = E.tiers[A.ev_tier[i]], name = E.names[A.ev_name[i]], act = E.actions[A.ev_action[i]];
  let t = EVENT_TEXT[tier + '/' + name];
  if (tier === 'RINGFIX' && name === 'release') t = 'released: ' + (RELEASE_TEXT[act] || act);
  return t || (tier + ' ' + name + (act ? ' (' + act + ')' : ''));
}
function rawDetail(i) {
  const d = M.H.events.details[M.A.ev_detail[i]] || '';
  return d.replace(/wire/gi, 'stream');
}

function eventRows(idx, limit) {
  const A = M.A, other = M.H.lanes.findIndex(l => l.key === 'other');
  const nOther = idx.filter(i => A.ev_lane[i] === other).length;
  if (!S.showOther) idx = idx.filter(i => A.ev_lane[i] !== other);
  const toggle = nOther ? '<div class="hint"><span class="act" data-toggle-other="1">' + (S.showOther ? 'hide' : 'show') +
    ' the ' + nOther + ' rows of other checks</span> (outlier tests, bookkeeping, wet delay carry)</div>' : '';
  const rows = idx.slice(0, limit || 400).map(i => {
    const sta = A.ev_sta[i] >= 0 ? M.names[A.ev_sta[i]] : '';
    const sat = A.ev_sat[i] >= 0 ? M.H.sats[A.ev_sat[i]] : '';
    const band = A.ev_band[i] >= 0 ? M.H.bands[A.ev_band[i]].split(':')[1] : '';
    const who = [sta, sat].filter(Boolean).join(' - ') + (band ? ' ' + band : '');
    return '<div data-ev="' + i + '"><span class="lane-dot" style="background:' + laneColor(A.ev_lane[i]) + '"></span>' +
      '<span class="t">' + clockOf(A.ev_ep[i]) + '</span>' + esc(eventText(i)) + (who ? ' <b>' + esc(who) + '</b>' : '') +
      '<div class="raw">' + esc(M.H.events.tiers[A.ev_tier[i]] + ' ' + M.H.events.names[A.ev_name[i]] + ' ' +
      M.H.events.actions[A.ev_action[i]] + ': ' + rawDetail(i)) + '</div></div>';
  });
  const more = idx.length > (limit || 400) ? '<div class="hint">' + (idx.length - (limit || 400)) + ' more not listed</div>' : '';
  return toggle + '<div class="evlist">' + (rows.join('') || '<div class="hint">none</div>') + more + '</div>';
}

function renderDetail() {
  const el = document.getElementById('detail');
  el.innerHTML = '';
  const sel = S.sel;
  if (!sel) renderOverview(el);
  else if (sel.kind === 'link') renderLink(el, sel);
  else if (sel.kind === 'sat') renderSat(el, sel);
  else if (sel.kind === 'sta') renderSta(el, sel);
  else if (sel.kind === 'events') renderEvents(el, sel);
  wireDetailClicks(el);
  updateDetailNow();
}

function nowBox(el) {
  const d = document.createElement('div');
  d.id = 'now-box';
  el.appendChild(d);
  return d;
}

function updateDetailNow() {
  const box = document.getElementById('now-box');
  if (!box) return;
  const sel = S.sel;
  let html = '';
  if (!sel) html = overviewNow();
  else if (sel.kind === 'link') html = linkNow(sel);
  else if (sel.kind === 'sat') html = satNow(sel);
  else if (sel.kind === 'sta') html = staNow(sel);
  box.innerHTML = html;
  wireDetailClicks(box);
}

// --- overview

function renderOverview(el) {
  const H = M.H, d = gpsDate(0);
  el.insertAdjacentHTML('beforeend', '<h2>' + esc(H.run) + '</h2><div class="sub">' +
    d.toISOString().slice(0, 10) + ' (day ' + dayOfYear(d) + ' of ' + d.getUTCFullYear() + '), ' + M.nEp + ' epochs over ' +
    durationText(M.nEp) + ', ' + M.nSta + ' receivers, ' + M.nSat + ' satellites</div>');
  nowBox(el);
  hint(el, 'Click a link, a satellite or a receiver in the network to see its history; click a lane of the timeline ' +
    'to jump to its events. Arrow keys step one epoch (with Shift ten), the space bar plays. The yellow path is the chain ' +
    'of tree links from the selected node to the reference receiver.');
  const fams = H.families.map((f, i) => '<tr><td><span class="act" data-fam="' + i + '">' + esc(famLabel(f)) + '</span></td><td>' +
    (f.fixing ? 'held (' + f.held_link_epochs.toLocaleString() + ' link-epochs held)' : 'floats only') + '</td></tr>').join('');
  el.insertAdjacentHTML('beforeend', '<h3>Signal families</h3><table>' + fams + '</table>');
  const cfg = H.config || {};
  if (cfg.ring_fix && Object.keys(cfg.ring_fix).length) {
    el.insertAdjacentHTML('beforeend', '<h3>Fixing settings (from ' + esc(cfg.file || 'the config') + ')</h3><table class="kv">' +
      Object.entries(cfg.ring_fix).map(([k, v]) => '<tr><td>' + esc(k) + '</td><td>' + esc(JSON.stringify(v)) + '</td></tr>').join('') +
      '</table>');
  }
  const au = H.audits || {};
  if (au.right || au.wrong) {
    hint(el, 'Held whole numbers checked against the integers of the run\'s audit file: ' + (au.right || 0).toLocaleString() +
      ' link-epochs right, ' + (au.wrong || 0).toLocaleString() + ' wrong' +
      (au.unlisted ? ', ' + au.unlisted.toLocaleString() + ' not in the file' : '') + '.');
  }
}

function overviewNow() {
  const sl = M.A.sum_links;
  if (!sl) return '';
  const ne = M.nEp, nf = M.nFam;
  const rows = M.H.families.map((f, i) => {
    const n = sl[i * ne + S.ep], held = sl[(nf + i) * ne + S.ep], ref = sl[(3 * nf + i) * ne + S.ep];
    return '<tr><td>' + esc(famLabel(f)) + '</td><td class="num">' + n + '</td><td class="num">' + (f.fixing ? held : '') +
      '</td><td class="num">' + (f.fixing ? (n ? Math.round(100 * held / n) + ' %' : '') : '') + '</td><td class="num">' +
      (f.fixing ? ref : '') + '</td></tr>';
  }).join('');
  return '<h3>At ' + clockOf(S.ep) + ': links that are not tree links</h3><table><tr><th>signals</th><th class="num">links</th>' +
    '<th class="num">held</th><th class="num">share</th><th class="num">not yet</th></tr>' + rows + '</table>';
}

// --- link

function linkStrip(sel) {
  const cf = curFamily(), A = M.A;
  const codes = new Uint8Array(M.nEp);
  const s = M.nSta + sel.sat;
  for (let e = 0; e < M.nEp; e++) {
    const t1 = isTreeLink(cf.f.band1, sel.sta, s, e), t2 = isTreeLink(cf.f.band2, sel.sta, s, e);
    if (t1 && t2) { codes[e] = 1; continue; }
    if (t1 || t2) { codes[e] = 2; continue; }
    const r = sel.link >= 0 ? linkRowAt(sel.link, e) : -1;
    if (r < 0) continue;
    const k = stateKind(A.ce_state[r]);
    codes[e] = k === 'held' ? 3 : k === 'decided' ? 4 : k === 'refused' ? 5 : 6;
  }
  return codes;
}
const STRIP_LABELS = ['absent', 'tree link of both signals', 'tree link of one signal', 'held', 'decided', 'float, not yet held', 'float'];
function stripColors() { return [null, C.tree, withAlpha(C.tree, 0.45), C.held, C.decided, C.refused, C.float]; }

function renderLink(el, sel) {
  const cf = curFamily();
  if (!cf) { el.insertAdjacentHTML('beforeend', '<div class="hint">No signal family with links in this run.</div>'); return; }
  const f = cf.f;
  const staName = M.names[sel.sta], satName = M.H.sats[sel.sat];
  el.insertAdjacentHTML('beforeend', '<h2>Link <span class="act" data-node="' + sel.sta + '">' + esc(staName) + '</span> - ' +
    '<span class="act" data-node="' + (M.nSta + sel.sat) + '">' + esc(satName) + '</span></h2><div class="sub">' +
    esc(famLabel(f)) + '</div>');
  nowBox(el);
  const codes = linkStrip(sel);
  const counts = [0, 0, 0, 0, 0, 0, 0];
  for (const c of codes) counts[c]++;
  makeChart(chartEl(el, 'Over the run', 'strip', STRIP_LABELS.slice(1).map((t, i) => [stripColors()[i + 1], t]).filter((_x, i) => counts[i + 1])),
    { strip: { codes, colors: stripColors() }, noAxis: false });
  hint(el, ['tree link', 'held', 'float'].map((t, k) => {
    const n = k === 0 ? counts[1] + counts[2] : k === 1 ? counts[3] + counts[4] : counts[5] + counts[6];
    return t + ' ' + durationText(n);
  }).join(', ') + '.');
  holdHistory(el, sel);
  if (sel.link >= 0) linkCharts(el, sel, f);
  treeTargetChart(el, sel, cf);
  const elev = losElevation(sel.sta, sel.sat);
  if (elev) makeChart(chartEl(el, 'Elevation of the satellite seen from the receiver (degrees)', '', [[C.muted, 'elevation']]),
    { series: [{ y: elev, color: C.muted, width: 1.4 }], yRange: [0, 90], nTicks: 3, valueAt: e => fmt(elev[e], 0) + ' degrees' });
  const ev = selectionEvents();
  el.insertAdjacentHTML('beforeend', '<h3>Events of this link (' + (ev ? ev.idx.length : 0) + ')</h3>' + eventRows(ev ? ev.idx : []));
}

function linkCharts(el, sel, f) {
  const A = M.A, ne = M.nEp;
  const wl = new Float32Array(ne).fill(NaN), nl = new Float32Array(ne).fill(NaN);
  const wlLo = new Float32Array(ne).fill(NaN), wlHi = new Float32Array(ne).fill(NaN);
  const nlLo = new Float32Array(ne).fill(NaN), nlHi = new Float32Array(ne).fill(NaN);
  const res = new Float32Array(ne).fill(NaN);
  const s0 = A.link_start[sel.link], c = A.link_count[sel.link];
  let anyRes = false;
  for (let r = s0; r < s0 + c; r++) {
    const e = A.ce_ep[r], q = rowInfo(r);
    wl[e] = q.wlDist; nl[e] = q.nDist;
    wlLo[e] = q.wlDist - q.sWl; wlHi[e] = q.wlDist + q.sWl;
    nlLo[e] = q.nDist - q.sIf; nlHi[e] = q.nDist + q.sIf;
    if (isFinite(q.res)) { res[e] = q.res; anyRes = true; }
  }
  const wlMax = (M.H.config && M.H.config.ring_fix && M.H.config.ring_fix.wl_frac_max) || 0.25;
  const band = withAlpha(C.held, 0.18);
  makeChart(chartEl(el, 'Wide lane: float minus its whole number (cycles), band = one sigma', '', [[C.held, 'float minus whole number'], [C.refused, 'limit ' + wlMax]]), {
    series: [{ y: wl, color: C.held, width: 1.3 }], bands: [{ lo: wlLo, hi: wlHi, color: band }],
    hlines: [{ y: 0, color: C.muted, dash: [] }, { y: wlMax, color: C.refused }, { y: -wlMax, color: C.refused }],
    symmetric: true, minHalf: 0.3, yRange: [-0.6, 0.6], valueAt: e => fmtSigned(wl[e]),
  });
  makeChart(chartEl(el, 'Narrow lane (ionosphere-free, wide lane fixed): float minus its whole number (cycles)', 'tall', [[C.held, 'float minus whole number'], [C.refused, 'limit 0.20']]), {
    series: [{ y: nl, color: C.held, width: 1.3 }], bands: [{ lo: nlLo, hi: nlHi, color: band }],
    hlines: [{ y: 0, color: C.muted, dash: [] }, { y: 0.2, color: C.refused }, { y: -0.2, color: C.refused }],
    yRange: [-0.6, 0.6], valueAt: e => fmtSigned(nl[e]),
  });
  if (anyRes) {
    makeChart(chartEl(el, 'Post-fit ionosphere-free phase residual while held (m)', '', [[C.held, 'residual'], [C.release, 'release bound 0.03 m']]), {
      series: [{ y: res, color: C.held }], hlines: [{ y: 0.03, color: C.release }, { y: -0.03, color: C.release }, { y: 0, color: C.muted, dash: [] }],
      symmetric: true, minHalf: 0.04, valueAt: e => fmtSigned(res[e], 4) + ' m',
    });
  }
  const rf = (M.H.config && M.H.config.ring_fix) || {};
  const gate = rf.gate === 'odds'
    ? 'the odds of the nearest whole number against the next exceed a million to one on the narrow and the wide lane' +
      (rf.sigma_scale && rf.sigma_scale !== 1 ? ' (sigma scaled by ' + rf.sigma_scale + ')' : '')
    : 'the narrow lane\'s sigma is at most 0.10 cycle';
  hint(el, 'While held the whole numbers are the held ones; otherwise the nearest. ' + (f.fixing ? 'The fixing holds a ' +
    'link when ' + gate + ', the narrow lane is within 0.20 cycle and the wide lane within ' + wlMax + ' of a whole ' +
    'number, with the same whole numbers for 10 epochs in a row and no event on the link in the last 10 min.' :
    'No fixing runs on these signals: the link stays a float.'));
}

/** The link's fixing history from its RINGFIX events: decided, released (with the cause), became a tree link,
 * carried the tree through a re-host; each release with how long the hold lasted. */
function holdHistory(el, sel) {
  const ev = selectionEvents();
  if (!ev) return;
  const A = M.A, E = M.H.events;
  const rows = [];
  let since = -1;
  for (const i of ev.idx) {
    if (E.tiers[A.ev_tier[i]] !== 'RINGFIX') continue;
    const name = E.names[A.ev_name[i]], act = E.actions[A.ev_action[i]], e = A.ev_ep[i];
    let what = eventText(i), extra = '';
    if (name === 'hold') since = e;
    if (name === 'release' || name === 'to_tree') {
      if (since >= 0) extra = 'held ' + durationText(e - since);
      since = -1;
    }
    if (name === 'release') what = 'released: ' + (RELEASE_TEXT[act] || act);
    rows.push('<tr><td><span class="act" data-ep="' + e + '">' + clockOf(e) + '</span></td><td>' + esc(what) + '</td><td>' + esc(extra) + '</td></tr>');
  }
  if (!rows.length) return;
  el.insertAdjacentHTML('beforeend', '<h3>Decided, held, released</h3><table>' + rows.join('') + '</table>');
}

function treeTargetChart(el, sel, cf) {
  const s = M.nSta + sel.sat, ne = M.nEp;
  const series = [];
  const key = [];
  [[cf.f.band1, cf.f.b1, C.tree], [cf.f.band2, cf.f.b2, C.held]].forEach(([b, name, color]) => {
    const y = new Float32Array(ne).fill(NaN);
    let any = false;
    for (let e = 0; e < ne; e++) {
      if (!isTreeLink(b, sel.sta, s, e)) continue;
      const child = treeParent(b, s, e) === sel.sta ? s : sel.sta;
      const t = treeTarget(b, child, e);
      if (t != null) { y[e] = t; any = true; }
    }
    if (any) { series.push({ y, color, step: true, width: 1.6 }); key.push([color, name]); }
  });
  if (!series.length) return;
  makeChart(chartEl(el, 'Whole number of the tree link (cycles)', '', key), { series, nTicks: 3, yFmt: v => v.toFixed(0) });
}

function linkNow(sel) {
  const cf = curFamily();
  if (!cf) return '';
  const f = cf.f, e = S.ep, s = M.nSta + sel.sat;
  const t1 = isTreeLink(f.band1, sel.sta, s, e), t2 = isTreeLink(f.band2, sel.sta, s, e);
  const rows = [];
  if (t1 || t2) {
    const parts = [];
    for (const [b, name, on] of [[f.band1, f.b1, t1], [f.band2, f.b2, t2]]) {
      if (!on) continue;
      const child = treeParent(b, s, e) === sel.sta ? s : sel.sta;
      const t = treeTarget(b, child, e);
      parts.push(name + ' ' + (t == null ? '?' : t));
    }
    rows.push(['now', '<span class="state-tree">tree link of ' + [t1 && f.b1, t2 && f.b2].filter(Boolean).join(' and ') + '</span>']);
    rows.push(['whole numbers', parts.join(', ')]);
  }
  const r = sel.link >= 0 ? linkRowAt(sel.link, e) : -1;
  if (r >= 0) {
    const q = rowInfo(r), k = stateKind(q.state);
    rows.push(['now', '<span class="state-' + k + '">' + esc(M.H.states[q.state]) + '</span>']);
    rows.push([k === 'held' || k === 'decided' ? 'held whole numbers' : 'nearest whole numbers',
      f.b1 + ' ' + q.n1 + ', ' + f.b2 + ' ' + q.n2 + ', wide lane ' + q.wl]);
    const pinned = k === 'held' ? ' <span class="state-float">(pinned by the hold)</span>' : '';
    rows.push(['wide-lane float', fmt(q.wlFloat, 3) + ' (' + fmtSigned(q.wlDist) + ' from ' + q.wl + ', sigma ' + fmt(q.sWl, 3) + ')' + pinned]);
    rows.push(['narrow-lane float', fmt(q.nFloat, 3) + ' (' + fmtSigned(q.nDist) + ' from ' + q.n1 + ', sigma ' + fmt(q.sIf, 3) + ')' + pinned]);
    if (q.ring) rows.push(['ring', q.ring + ' (the larger hop count of its two ends)']);
    if (isFinite(q.res)) rows.push(['residual', fmtSigned(q.res, 4) + ' m']);
  }
  if (!rows.length) rows.push(['now', 'not tracked at this epoch']);
  const elev = M.A.los_el ? M.A.los_el[(sel.sta * M.nSat + sel.sat) * M.nEp + e] : 255;
  if (elev !== 255) rows.push(['elevation', elev + ' degrees']);
  const dS = treeDepth(cf.b, sel.sta, e), dT = treeDepth(cf.b, s, e);
  rows.push(['hops (' + cf.sig + ')', M.names[sel.sta] + ' ' + (dS >= 0 ? dS : '-') + ', ' + M.H.sats[sel.sat] + ' ' + (dT >= 0 ? dT : '-')]);
  return '<h3>At ' + clockOf(e) + '</h3><table class="kv">' + rows.map(([k, v]) => '<tr><td>' + esc(k) + '</td><td>' + v + '</td></tr>').join('') + '</table>';
}

// --- satellite

function renderSat(el, sel) {
  const cf = curFamily(), f = cf ? cf.f : null, sat = sel.node - M.nSta, name = M.H.sats[sat];
  el.insertAdjacentHTML('beforeend', '<h2>Satellite ' + esc(name) + '</h2><div class="sub">' + esc(sysName(name[0])) +
    (!f || name[0] === f.sys ? '' : ' (not of the drawn signals: pick its family above)') + '</div>');
  nowBox(el);
  if (f && M.hasTree && name[0] === f.sys) hopsChart(el, sel.node, f);
  if (cf) satLevelChart(el, sat, cf);
  const clk = satSeries('clk', sat);
  if (clk) makeChart(chartEl(el, 'Clock correction emitted (m)', '', [[C.ink, 'clock']]), { series: [{ y: clk, color: C.ink }], robust: true, valueAt: e => fmt(clk[e], 4) + ' m' });
  biasChart(el, sat, 'pb', 'Phase bias emitted, change from its median (m)');
  biasChart(el, sat, 'cb', 'Code bias emitted, change from its median (m)');
  const ev = selectionEvents();
  el.insertAdjacentHTML('beforeend', '<h3>Events of this satellite (' + (ev ? ev.idx.length : 0) + ')</h3>' + eventRows(ev ? ev.idx : []));
}
/** Hops of a node on both signals of family f over the run, with a mark wherever the tree moved it. */
function hopsChart(el, node, f) {
  const ne = M.nEp, h1 = new Float32Array(ne).fill(NaN), h2 = new Float32Array(ne).fill(NaN);
  for (let e = 0; e < ne; e++) {
    const a = treeDepth(f.band1, node, e), b = treeDepth(f.band2, node, e);
    if (a >= 0) h1[e] = a;
    if (b >= 0) h2[e] = b + 0.12;                        // drawn a hair apart so equal hops stay visible
  }
  const moves = treeMoves(f.band1, node);
  makeChart(chartEl(el, 'Hops from the reference receiver; marks at the top: the tree moved it on ' + f.b1 + ' (' + moves.length + ')', '',
    [[C.tree, f.b1], [C.held, f.b2], [C.release, 'moved']]), {
    series: [{ y: h1, color: C.tree, step: true, width: 1.6 }, { y: h2, color: C.held, step: true, width: 1.2 }],
    ticks: moves.map(e => ({ e, color: C.release })),
    nTicks: 3, zeroBased: true, yFmt: v => v.toFixed(0),
    valueAt: e => f.b1 + ' ' + (isFinite(h1[e]) ? h1[e] : '-') + ', ' + M.H.tree_rows[treeRow(f.band1, node, e)],
  });
}
function hasFinite(a) { for (let i = 0; i < a.length; i++) if (isFinite(a[i])) return true; return false; }
function median(a) {
  const v = Array.from(a).filter(isFinite).sort((p, q) => p - q);
  return v.length ? v[v.length >> 1] : NaN;
}

/** Each signal's emitted bias less its median over the run: offsets of tens of metres would hide the moves. */
function biasChart(el, sat, kind, title) {
  const tab = kind === 'pb' ? M.H.phase_signals : M.H.code_signals;
  const sigs = tab.filter(s => s[0] && satSeries(kind, sat, s) && hasFinite(satSeries(kind, sat, s)));
  if (!sigs.length) return;
  const cols = sigs.map((_s, i) => rampColor(window.NV_ASSETS.colormaps.viridis, sigs.length > 1 ? 0.85 * i / (sigs.length - 1) : 0.3));
  const series = sigs.map((s, i) => {
    const y = satSeries(kind, sat, s), m = median(y);
    return { y: Float32Array.from(y, v => v - m), color: cols[i], med: m };
  });
  makeChart(chartEl(el, title, '', sigs.map((s, i) => [cols[i], s + ' (median ' + fmt(series[i].med, 3) + ')'])), {
    series, robust: true, valueAt: e => sigs.map((s, i) => s + ' ' + fmtSigned(series[i].y[e], 3)).join(', '),
  });
}

function satLevelChart(el, sat, cf) {
  const f = cf.f, fi = cf.fi;
  const l1 = satLevel(fi, 0, sat), l2 = satLevel(fi, 1, sat);
  if (!l1 || !hasFinite(l1)) return;
  const ne = M.nEp, nl = new Float32Array(ne).fill(NaN), wl = new Float32Array(ne).fill(NaN);
  for (let e = 0; e < ne; e++) {
    if (!isFinite(l1[e]) || !isFinite(l2[e])) continue;
    nl[e] = (f.f1 * l1[e] - f.f2 * l2[e]) / (f.f1 - f.f2);
    wl[e] = l1[e] - l2[e];
  }
  const A = M.A, jl = M.jumps.get(fi + '|' + sat) || [];
  const clsColor = [null, C.whole, C.iono, C.frac];
  const dots = jl.map(i => ({ e: A.jp_ep[i], y: nl[A.jp_ep[i]], color: clsColor[A.jp_cls[i]], r: 3.2 }));
  const n = [0, 0, 0, 0];
  for (const i of jl) n[A.jp_cls[i]]++;
  makeChart(chartEl(el, 'Correction level: the satellite\'s own steps added up (cycles)', 'tall',
    [[C.ink, 'narrow lane'], [C.muted, 'wide lane'], [C.whole, 'whole jump ' + n[1]], [C.iono, 'ionosphere-like ' + n[2]], [C.frac, 'fraction ' + n[3]]]), {
    series: [{ y: nl, color: C.ink, width: 1.3 }, { y: wl, color: C.muted, width: 1, dash: [3, 2] }], dots,
    valueAt: e => 'narrow ' + fmt(nl[e], 3) + ', wide ' + fmt(wl[e], 3),
  });
  hint(el, 'A jump is the step of the satellite\'s emitted correction level between two epochs after the step all ' +
    'satellites share is removed (tolerance ' + M.H.jump_tol + ' cycle): whole cycles on both signals (a re-pin), ' +
    'ionosphere-like (the ionosphere-free level unchanged) or a fraction of a cycle (the level a user holds moves).');
}

function satNow(sel) {
  const cf = curFamily(), e = S.ep, n = sel.node, name = M.names[n];
  const rows = [];
  if (!cf) return '<h3>At ' + clockOf(e) + '</h3><div class="hint">No signal family with a tree in this run.</div>';
  const f = cf.f;
  if (name[0] === f.sys && M.hasTree) {
    for (const [b, sig] of [[f.band1, f.b1], [f.band2, f.b2]]) {
      const d = treeDepth(b, n, e), p = treeParent(b, n, e), ch = treeChangeText(b, n, e);
      rows.push(['hops on ' + sig, d >= 0 ? d + (p >= 0 ? ', parent <span class="act" data-node="' + p + '">' + esc(M.names[p]) + '</span>' : '') +
        (ch ? ' <span class="state-refused">(' + esc(ch) + ' now)</span>' : '') : 'not on this tree']);
    }
    const gr = G.gr && G.gr.cf && G.gr.cf.fi === cf.fi ? G.gr : collectGraph(e);
    const tot = gr.inTotal[n], wh = gr.inWhole[n];
    rows.push(['links towards the reference', tot ? wh + ' of ' + tot + ' are whole numbers' : 'none']);
    rows.push(['tied to the reference by whole numbers only', tot ? (wh === tot ? 'yes' : 'no') : 'n/a']);
    const links = gr.links.filter(lk => lk.s === n).sort((p, q) => gr.depth[p.a] - gr.depth[q.a]);
    if (links.length) {
      rows.push(['links', links.map(lk => '<span class="act" data-link="' + lk.a + ',' + (n - M.nSta) + '">' +
        esc(shortSta(M.names[lk.a])) + '</span> <span class="state-' + kindClass(lk.kind) + '">' + kindWord(lk.kind) + '</span>').join(', ')]);
    }
  }
  const jl = M.jumps.get(cf.fi + '|' + (n - M.nSta)) || [];
  const A = M.A, here = jl.filter(i => A.jp_ep[i] === e);
  if (here.length) rows.push(['jump now', here.map(i => ['', 'whole', 'ionosphere-like', 'fraction'][A.jp_cls[i]] + ' (narrow lane ' + fmtSigned(A.jp_dn[i]) + ')').join(', ')]);
  return '<h3>At ' + clockOf(e) + '</h3><table class="kv">' + rows.map(([k, v]) => '<tr><td>' + esc(k) + '</td><td>' + v + '</td></tr>').join('') + '</table>';
}
function kindWord(k) { return { tree: 'tree', treeOther: 'tree (other signal)', held: 'held', decided: 'decided', refused: 'not yet', float: 'float' }[k] || k; }
function kindClass(k) { return k === 'treeOther' ? 'tree' : k === 'decided' ? 'held' : k; }

// --- receiver

function renderSta(el, sel) {
  const n = sel.node, st = M.H.stations[n];
  el.insertAdjacentHTML('beforeend', '<h2>Receiver ' + esc(st.name) + '</h2><div class="sub">' + esc(st.role || '') +
    (st.lat != null ? ', latitude ' + st.lat.toFixed(2) + ', longitude ' + st.lon.toFixed(2) : '') + '</div>');
  nowBox(el);
  if (curFamily() && M.hasTree) hopsChart(el, n, curFamily().f);
  const z = rxSeries('rx_zwd', n), zs = rxSeries('rx_zwd_sd', n);
  if (z) {
    const lo = z.map((v, i) => v - zs[i]), hi = z.map((v, i) => v + zs[i]);
    makeChart(chartEl(el, 'Wet delay at the zenith (m), band = one sigma; scale from the 1st to the 99th percentile', '', [[C.held, 'wet delay']]), {
      series: [{ y: z, color: C.held }], bands: [{ lo, hi, color: withAlpha(C.held, 0.15) }], valueAt: e => fmt(z[e], 4) + ' m',
      robust: true,
    });
  }
  const ck = rxSeries('rx_clk', n);
  if (ck) makeChart(chartEl(el, 'Receiver clock (m)', '', [[C.ink, 'clock']]), { series: [{ y: ck, color: C.ink }], robust: true, valueAt: e => fmt(ck[e], 3) + ' m' });
  if (M.A.rx_rpb && curFamily()) {
    const cf = curFamily();
    const series = [], key = [];
    [[cf.f.band1, cf.f.b1, C.tree], [cf.f.band2, cf.f.b2, C.held]].forEach(([b, name, color]) => {
      const y = rxSeries('rx_rpb', n, b);
      if (y && hasFinite(y)) { series.push({ y, color }); key.push([color, name]); }
    });
    if (series.length) makeChart(chartEl(el, 'Receiver phase bias (m)', '', key), { series, robust: true });
  } else if (!M.A.rx_rpb) hint(el, 'Receiver phase bias: not traced in this run (key network.trace_rpb_states).');
  const ev = selectionEvents();
  const A = M.A, al = M.H.lanes.findIndex(l => l.key === 'alarm');
  const alarms = ev ? ev.idx.filter(i => A.ev_lane[i] === al) : [];
  el.insertAdjacentHTML('beforeend', '<h3>Alarms at this receiver (' + alarms.length + ')</h3>' + eventRows(alarms, 100));
  el.insertAdjacentHTML('beforeend', '<h3>All events of this receiver (' + (ev ? ev.idx.length : 0) + ')</h3>' + eventRows(ev ? ev.idx : []));
}
function staNow(sel) {
  const cf = curFamily(), e = S.ep, n = sel.node;
  const rows = [];
  if (!cf) {
    const z = rxSeries('rx_zwd', n);
    if (z) rows.push(['wet delay', fmt(z[e], 4) + ' m']);
    return '<h3>At ' + clockOf(e) + '</h3><table class="kv">' + rows.map(([k, v]) => '<tr><td>' + esc(k) + '</td><td>' + v + '</td></tr>').join('') + '</table>';
  }
  const f = cf.f;
  if (M.hasTree) {
    for (const [b, sig] of [[f.band1, f.b1], [f.band2, f.b2]]) {
      const d = treeDepth(b, n, e), p = treeParent(b, n, e), ch = treeChangeText(b, n, e);
      rows.push(['hops on ' + sig, d >= 0 ? (p === -2 ? '0 (the reference receiver)' : d + (p >= 0 ? ', parent <span class="act" data-node="' + p + '">' + esc(M.names[p]) + '</span>' : '') +
        (ch ? ' <span class="state-refused">(' + esc(ch) + ' now)</span>' : '')) : 'not on this tree']);
    }
  }
  const z = rxSeries('rx_zwd', n);
  if (z) rows.push(['wet delay', fmt(z[e], 4) + ' m']);
  const gr = G.gr && G.gr.cf && G.gr.cf.fi === cf.fi ? G.gr : collectGraph(e);
  const links = gr.links.filter(lk => lk.a === n).sort((p, q) => gr.depth[p.s] - gr.depth[q.s]);
  if (links.length) {
    const cnt = {};
    for (const lk of links) cnt[lk.kind] = (cnt[lk.kind] || 0) + 1;
    rows.push(['links of ' + famLabel(f), Object.entries(cnt).map(([k, v]) => v + ' ' + kindWord(k)).join(', ')]);
    rows.push(['', links.map(lk => '<span class="act" data-link="' + n + ',' + (lk.s - M.nSta) + '">' + esc(M.names[lk.s]) +
      '</span> <span class="state-' + kindClass(lk.kind) + '">' + kindWord(lk.kind) + '</span>').join(', ')]);
  }
  return '<h3>At ' + clockOf(e) + '</h3><table class="kv">' + rows.map(([k, v]) => '<tr><td>' + esc(k) + '</td><td>' + v + '</td></tr>').join('') + '</table>';
}

// --- events of one epoch

function renderEvents(el, sel) {
  const A = M.A, e = sel.ep;
  const idx = [];
  for (let i = M.evOff[e]; i < M.evOff[e + 1]; i++) idx.push(i);
  if (sel.lane >= 0) idx.sort((p, q) => (A.ev_lane[q] === sel.lane) - (A.ev_lane[p] === sel.lane));
  el.insertAdjacentHTML('beforeend', '<h2>Events at ' + clockOf(e) + '</h2><div class="sub">' + idx.length +
    ' events at this epoch' + (sel.lane >= 0 ? ', ' + esc(M.H.lanes[sel.lane].label.toLowerCase()) + ' first' : '') +
    '. Click a row to select its link or node.</div>');
  el.insertAdjacentHTML('beforeend', eventRows(idx, 600));
}

function wireDetailClicks(root) {
  root.querySelectorAll('[data-node]').forEach(x => x.addEventListener('click', () => selectNode(+x.dataset.node)));
  root.querySelectorAll('[data-link]').forEach(x => x.addEventListener('click', () => {
    const [a, s] = x.dataset.link.split(',').map(Number);
    selectLink(a, s);
  }));
  root.querySelectorAll('[data-fam]').forEach(x => x.addEventListener('click', () => setFamily(+x.dataset.fam)));
  root.querySelectorAll('[data-toggle-other]').forEach(x => x.addEventListener('click', () => { S.showOther = !S.showOther; renderDetail(); }));
  root.querySelectorAll('[data-ep]').forEach(x => x.addEventListener('click', () => setEp(+x.dataset.ep)));
  root.querySelectorAll('[data-ev]').forEach(x => x.addEventListener('click', () => {
    const i = +x.dataset.ev, A = M.A;
    setEp(A.ev_ep[i]);
    if (A.ev_sta[i] >= 0 && A.ev_sat[i] >= 0) selectLink(A.ev_sta[i], A.ev_sat[i], A.ev_band[i]);
    else if (A.ev_sat[i] >= 0) selectNode(M.nSta + A.ev_sat[i]);
    else if (A.ev_sta[i] >= 0) selectNode(A.ev_sta[i]);
  }));
}

// ============================================================================================ 8. summaries over the run

function renderSummary() {
  const box = document.getElementById('summary-charts');
  box.innerHTML = '';
  const fig = (title, keyItems) => {
    const f = document.createElement('figure');
    f.innerHTML = '<figcaption>' + esc(title) + '</figcaption>';
    const cv = document.createElement('canvas');
    f.appendChild(cv);
    if (keyItems) {
      const k = document.createElement('div');
      k.className = 'chart-key';
      k.innerHTML = keyItems.map(([c, t]) => '<span><i style="background:' + c + '"></i>' + esc(t) + '</span>').join('');
      f.appendChild(k);
    }
    box.appendChild(f);
    return cv;
  };
  const sl = M.A.sum_links, ne = M.nEp, nf = M.nFam;
  if (sl && M.hasFixing) {
    const fams = M.H.families.map((f, i) => [f, i]).filter(([f]) => f.fixing);
    const cols = fams.map((_x, k) => rampColor(window.NV_ASSETS.colormaps.viridis, fams.length > 1 ? 0.8 * k / (fams.length - 1) : 0.25));
    const series = fams.map(([_f, i], k) => {
      const y = new Float32Array(ne);
      for (let e = 0; e < ne; e++) { const n = sl[i * ne + e]; y[e] = n ? 100 * sl[(nf + i) * ne + e] / n : NaN; }
      return { y, color: cols[k], width: 1.6 };
    });
    makeChart(fig('Share of the links that are not tree links held at whole numbers (%)', fams.map(([f], k) => [cols[k], famLabel(f)])),
      { series, yRange: [0, 100], nTicks: 4, valueAt: e => series.map(s => fmt(s.y[e], 0) + ' %').join(', ') });
  }
  const cf = curFamily();
  if (sl && cf) {
    const i = cf.fi, held = new Float32Array(ne), notyet = new Float32Array(ne), all = new Float32Array(ne);
    for (let e = 0; e < ne; e++) {
      all[e] = sl[i * ne + e]; held[e] = sl[(nf + i) * ne + e] + sl[(2 * nf + i) * ne + e]; notyet[e] = sl[(3 * nf + i) * ne + e];
    }
    const tree = new Float32Array(ne);
    if (M.hasTree) for (let e = 0; e < ne; e++) {
      let c = 0;
      for (let n = M.nSta; n < M.nNode; n++) if (treeParent(cf.f.band1, n, e) >= 0) c++;
      for (let n = 0; n < M.nSta; n++) if (treeParent(cf.f.band1, n, e) >= 0) c++;
      tree[e] = c;
    }
    makeChart(fig('Links of ' + famLabel(cf.f) + ' (count)', [[C.tree, 'tree links of ' + cf.f.b1], [C.float, 'not tree links'], [C.held, 'held'], [C.refused, 'not yet held']]), {
      series: [{ y: tree, color: C.tree }, { y: all, color: C.float }, { y: held, color: C.held, width: 1.6 }].concat(cf.f.fixing ? [{ y: notyet, color: C.refused }] : []),
      zeroBased: true, nTicks: 4, valueAt: e => 'tree ' + tree[e] + ', other ' + all[e] + ', held ' + held[e],
    });
  }
  jumpSummary(fig, cf);
  alarmSummary(fig);
}

function jumpSummary(fig, cf) {
  const tab = (M.H.jump_tables || []).find(t => t.family === (cf ? cf.fi : -1));
  if (!tab) return;
  const binEp = Math.round(3600000 / M.step), nh = tab.sat_hours.length;
  const hopsName = ['not on both trees', '1 hop', '3 hops', '5 hops', '7 hops or more'];
  const clsCol = [C.whole, C.iono, C.frac];
  const bars = [];
  for (let h = 0; h < nh; h++) {
    for (let k = 1; k <= 4; k++) {
      const sh = tab.sat_hours[h][k];
      if (!(sh > 0.2)) continue;
      const w = binEp / 4.6, e0 = h * binEp + (k - 1) * (binEp / 4.2) + 2;
      bars.push({ e0, e1: e0 + w, stack: tab.counts[h][k].map((c, j) => ({ v: c / sh, color: clsCol[j] })), label: ['', '1', '3', '5', '7+'][k] });
    }
  }
  makeChart(fig('Jumps of the corrections per satellite-hour, ' + famLabel(cf.f) + '; in each hour one bar per hops class (1, 3, 5, 7+)',
    [[C.whole, 'whole cycles'], [C.iono, 'ionosphere-like'], [C.frac, 'fraction of a cycle']]),
  { bars, zeroBased: true, nTicks: 4, valueAt: e => {
    const h = Math.floor(e / binEp);
    if (h >= nh) return '';
    return 'hour ' + h + ': ' + [1, 2, 3, 4].map(k => hopsName[k] + ' ' + (tab.sat_hours[h][k] > 0.2 ?
      tab.counts[h][k].map(c => (c / tab.sat_hours[h][k]).toFixed(1)).join('/') : '-')).join('; ');
  } });
}

/** Per 10 minutes: counts of the events of some lanes, or of one lane split by its action (the release cause). */
function binnedBars(groups) {
  const bin = Math.max(1, Math.round(600000 / M.step)), A = M.A, bars = [];
  for (let e0 = 0; e0 < M.nEp; e0 += bin) {
    const v = groups.map(() => 0);
    for (let i = M.evOff[e0]; i < M.evOff[Math.min(M.nEp, e0 + bin)]; i++) {
      const g = groups.findIndex(gr => gr.match(i, A));
      if (g >= 0) v[g]++;
    }
    bars.push({ e0, e1: e0 + bin, stack: groups.map((gr, j) => ({ v: v[j], color: gr.color })) });
  }
  return bars;
}

function alarmSummary(fig) {
  if (!M.nEv) return;
  const lane = k => M.H.lanes.findIndex(l => l.key === k);
  const rel = lane('release'), acts = M.H.events.actions;
  if (M.laneCount[rel].some(c => c > 0)) {
    const causes = [['slip', C.slip], ['refloat', C.alarm], ['gap', C.gap], ['chain', C.tree], ['monitor', C.coderef]];
    makeChart(fig('Releases of held links per 10 minutes, by cause', causes.map(([c, col]) => [col, RELEASE_TEXT[c] || c])), {
      bars: binnedBars(causes.map(([c, color]) => ({ color, match: (i, A) => A.ev_lane[i] === rel && acts[A.ev_action[i]] === c }))),
      zeroBased: true, nTicks: 4,
    });
  }
  const al = lane('alarm'), sl = lane('slip');
  makeChart(fig('Alarms and slips per 10 minutes', [[C.alarm, 'alarms'], [C.slip, 'slips']]), {
    bars: binnedBars([{ color: C.alarm, match: (i, A) => A.ev_lane[i] === al }, { color: C.slip, match: (i, A) => A.ev_lane[i] === sl }]),
    zeroBased: true, nTicks: 4,
  });
}

// ============================================================================================ 9. legend and missing parts

const LEGEND = [
  ['Reference receiver', 'The receiver at the centre of a signal\'s tree. Its receiver phase bias is fixed; every other receiver and satellite of the tree is tied to it.'],
  ['Tree link', 'A receiver-satellite link that the tree uses to tie a node to the reference receiver. Its ambiguity is a whole number by definition (the chain pins it). Each signal has its own tree; the dashed links are tree links of the other signal of the pair only.'],
  ['Held link', 'A link that is not a tree link and whose whole numbers on both signals the network fixing holds (a tight prior in the network solve). It is released at a slip, a gap, a change of the tree around it, a re-opened float or a residual above 3 cm.'],
  ['Float link', 'A link whose ambiguity is estimated as a real number. On signals with fixing, orange links are floats the fixing has not (yet) held; the detail of a link says which test it failed.'],
  ['Hop', 'The number of tree links between the reference receiver and a node. Satellites sit at odd hops (1, 3, 5, ...), receivers at even hops. The rings of the picture are the hops of the chosen signal\'s tree.'],
  ['Ring of a link', 'The larger hop count of its two ends. The fixing works outward ring by ring.'],
  ['Wide lane', 'The difference of the two signals\' ambiguities, in cycles of the wide lane (86 cm for GPS L1/L2, 75 cm for Galileo E1/E5a). Its float reaches a whole number earlier than each signal\'s.'],
  ['Narrow lane', 'The ionosphere-free combination of the two ambiguities with the wide lane fixed, in narrow-lane cycles (about 11 cm). It is the quantity that is held last; its distance from a whole number and its sigma decide.'],
  ['Jump', 'A step of a satellite\'s emitted correction level between two epochs, after the step all satellites share is removed. Whole: both signals move by whole cycles (a re-pin). Ionosphere-like: the ionosphere-free level is unchanged. Fraction: the ionosphere-free level moves by a part of a cycle, which a user with a float solution feels.'],
  ['Node colour', 'The share of a node\'s links towards the reference receiver (to nodes of fewer hops) that are whole numbers: tree links or held links. Yellow: every path inward is made of whole numbers.'],
  ['Alarm', 'A residual check that flagged or re-opened something: the post-fit residual test, a re-opened carried float, a gross error on a line of sight, a satellite clock leaving its anchor.'],
  ['Code reference', 'Events of the code biases that define the clock\'s reference (a new code signal of a satellite, a re-seed, a move of the clock to another code pair).'],
];

function renderLegend() {
  document.getElementById('legend-list').innerHTML = LEGEND.map(([t, d]) => '<dt>' + esc(t) + '</dt><dd>' + esc(d) + '</dd>').join('');
}

function renderMissing() {
  const box = document.getElementById('missing');
  const miss = M.H.missing || [];
  const notes = [];
  if (!M.hasFixing && M.hasLinks) notes.push('No fixing in this run (<code>network.ring_fix.enable</code> off): every link that is not a tree link is a float.');
  if (miss.length) {
    notes.push('Not in this run: ' + miss.map(m => esc(m.part) + ' (<code>' + esc(m.file) + '</code>, key <code>' + esc(m.key) + '</code>)').join('; ') +
      '. <code>netview.py arm</code> writes a config copy with the trace keys on.');
  }
  if (!notes.length) return;
  box.innerHTML = notes.join('<br>');
  box.hidden = false;
}

// ============================================================================================ 10. interaction and start

function setEp(e) {
  e = Math.max(0, Math.min(M.nEp - 1, e | 0));
  if (e === S.ep && G.gr) return;
  S.ep = e;
  document.getElementById('slider').value = e;
  refreshTime();
}
function refreshTime() {
  updateTimeLabel();
  drawGraph();
  drawTimeline();
  updateDetailNow();
  drawAllCharts();
  saveHash();
}
function setFamily(fi) {
  S.fam = fi;
  document.getElementById('family').value = fi;
  fillBandSelect();
  const sys = M.H.families[fi].sys;
  const selSat = S.sel && (S.sel.kind === 'link' ? S.sel.sat : S.sel.kind === 'sat' ? S.sel.node - M.nSta : -1);
  if (selSat != null && selSat >= 0 && M.H.sats[selSat][0] !== sys) S.sel = null;     // not of these signals
  if (S.sel && S.sel.kind === 'link') {
    S.sel.link = linkOf(S.fam, S.sel.sta, S.sel.sat);
    S.sel._ev = null;
  }
  TL.cache = null;
  drawGraph(); drawTimeline(); renderDetail(); renderSummary(); saveHash();
}
function selectNode(n) {
  if (n == null || n < 0) return;
  S.sel = { kind: n < M.nSta ? 'sta' : 'sat', node: n };
  if (n >= M.nSta) {
    const sys = M.names[n][0];
    if (curFamily() && curFamily().f.sys !== sys) {
      const fi = M.H.families.findIndex(f => f.sys === sys);
      if (fi >= 0) { setFamilyQuiet(fi); }
    }
  }
  afterSelect();
}
function selectLink(sta, sat) {
  const sys = M.H.sats[sat][0];
  if (curFamily() && curFamily().f.sys !== sys) {
    const fi = M.H.families.findIndex(f => f.sys === sys && f.fixing);
    setFamilyQuiet(fi >= 0 ? fi : M.H.families.findIndex(f => f.sys === sys));
  }
  S.sel = { kind: 'link', sta, sat, link: linkOf(S.fam, sta, sat) };
  afterSelect();
}
function setFamilyQuiet(fi) {
  if (fi < 0) return;
  S.fam = fi;
  document.getElementById('family').value = fi;
  fillBandSelect();
  renderSummary();
}
function afterSelect() {
  TL.cache = null;
  renderDetail(); drawGraph(); drawTimeline(); saveHash();
}
function clearSelection() { S.sel = null; afterSelect(); }

function fillBandSelect() {
  const f = M.H.families[S.fam], sel = document.getElementById('band');
  sel.innerHTML = '';
  if (!f) return;
  [f.b1, f.b2].forEach((b, i) => sel.insertAdjacentHTML('beforeend', '<option value="' + i + '">' + esc(b) + '</option>'));
  sel.value = S.bandSel;
}

function play() {
  S.playing = !S.playing;
  document.getElementById('play').innerHTML = S.playing ? '&#10074;&#10074;' : '&#9654;';
  if (!S.playing) return;
  let last = performance.now(), acc = 0;
  const tick = now => {
    if (!S.playing) return;
    acc += (now - last) / 1000 * S.speed;
    last = now;
    if (acc >= 1) {
      const n = Math.floor(acc);
      acc -= n;
      if (S.ep + n >= M.nEp - 1) { setEp(M.nEp - 1); play(); return; }
      setEp(S.ep + n);
    }
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

function saveHash() {
  const p = new URLSearchParams();
  p.set('t', S.ep); p.set('f', S.fam); p.set('b', S.bandSel);
  if (S.layout !== 'rings') p.set('l', S.layout);
  if (S.sel && S.sel.kind === 'link') p.set('s', 'link:' + M.names[S.sel.sta] + ':' + M.H.sats[S.sel.sat]);
  else if (S.sel && (S.sel.kind === 'sta' || S.sel.kind === 'sat')) p.set('s', 'node:' + M.names[S.sel.node]);
  try { history.replaceState(null, '', '#' + p.toString()); } catch (_e) { /* file:// may refuse; harmless */ }
  broadcast();
}

// --- two pages side by side (netview.py compare): each page tells its frame what it shows, the frame tells the other

const SYNC = { inFrame: window.parent !== window, applying: false };
function broadcast() {
  if (!SYNC.inFrame || SYNC.applying) return;
  const sel = S.sel;
  let s = '';
  if (sel && sel.kind === 'link') s = 'link:' + M.names[sel.sta] + ':' + M.H.sats[sel.sat];
  else if (sel && (sel.kind === 'sta' || sel.kind === 'sat')) s = 'node:' + M.names[sel.node];
  parent.postMessage({ nv: 'sync', ms: absMs(S.ep), fam: M.H.families[S.fam] && M.H.families[S.fam].key, band: S.bandSel,
    layout: S.layout, sel: s }, '*');
}
function applySync(d) {
  SYNC.applying = true;
  try {
    const fi = M.H.families.findIndex(f => f.key === d.fam);
    if (fi >= 0 && fi !== S.fam) setFamily(fi);
    if (d.band != null && d.band !== S.bandSel) { S.bandSel = d.band; fillBandSelect(); }
    if (d.layout && d.layout !== S.layout) { S.layout = d.layout; document.getElementById('layout').value = d.layout; }
    const want = d.sel || '';
    const have = S.sel && S.sel.kind === 'link' ? 'link:' + M.names[S.sel.sta] + ':' + M.H.sats[S.sel.sat]
      : S.sel && (S.sel.kind === 'sta' || S.sel.kind === 'sat') ? 'node:' + M.names[S.sel.node] : '';
    if (want !== have) {
      if (want.startsWith('link:')) {
        const [, a, b] = want.split(':');
        const sta = M.nodeIndex.get(a), sat = M.H.sats.indexOf(b);
        if (sta != null && sat >= 0) selectLink(sta, sat);
      } else if (want.startsWith('node:')) {
        const n = M.nodeIndex.get(want.slice(5));
        if (n != null) selectNode(n);
      } else if (S.sel && S.sel.kind !== 'events') clearSelection();
    }
    const e = epochAtMs(d.ms);
    if (e >= 0) setEp(e);
    drawGraph();
  } finally { SYNC.applying = false; }
}
window.addEventListener('message', ev => { if (ev.data && ev.data.nv === 'sync' && M.H) applySync(ev.data); });
function loadHash() {
  const p = new URLSearchParams(location.hash.slice(1));
  if (p.has('f') && +p.get('f') < M.nFam) S.fam = +p.get('f');
  if (p.has('b')) S.bandSel = +p.get('b') ? 1 : 0;
  if (p.has('t')) S.ep = Math.max(0, Math.min(M.nEp - 1, +p.get('t')));
  if (p.get('l') === 'map') S.layout = 'map';
  const s = p.get('s');
  if (s && s.startsWith('link:')) {
    const [, a, b] = s.split(':');
    const sta = M.nodeIndex.get(a), sat = M.H.sats.indexOf(b);
    if (sta != null && sat >= 0) S.sel = { kind: 'link', sta, sat, link: linkOf(S.fam, sta, sat) };
  } else if (s && s.startsWith('node:')) {
    const n = M.nodeIndex.get(s.slice(5));
    if (n != null) S.sel = { kind: n < M.nSta ? 'sta' : 'sat', node: n };
  }
}

function showTooltip(hit, x, y) {
  const tip = document.getElementById('tooltip');
  if (!hit) { tip.hidden = true; return; }
  const gr = G.gr, cf = gr.cf;
  let html = '';
  if (hit.kind === 'node') {
    const n = hit.node, d = gr.depth[n];
    html = '<b>' + esc(M.names[n]) + '</b> ' + (n < M.nSta ? 'receiver' : sysName(M.names[n][0]) + ' satellite') +
      '<br>' + (d === 0 ? 'reference receiver of ' + esc(cf.sig) : d > 0 ? d + ' hops on ' + esc(cf.sig) : 'not on the tree of ' + esc(cf.sig)) +
      (gr.inTotal[n] ? '<br>links towards the reference: ' + gr.inWhole[n] + ' of ' + gr.inTotal[n] + ' whole' : '');
  } else {
    const lk = hit.lk;
    html = '<b>' + esc(M.names[lk.a]) + ' - ' + esc(M.names[lk.s]) + '</b><br>' + esc(kindWord(lk.kind));
    if (lk.row >= 0) {
      const q = rowInfo(lk.row);
      html = '<b>' + esc(M.names[lk.a]) + ' - ' + esc(M.names[lk.s]) + '</b><br>' + esc(M.H.states[q.state]) +
        '<br>wide lane ' + fmtSigned(q.wlDist, 2) + ' from ' + q.wl + ' (sigma ' + fmt(q.sWl, 2) + ')' +
        '<br>narrow lane ' + fmtSigned(q.nDist, 2) + ' from ' + q.n1 + ' (sigma ' + fmt(q.sIf, 2) + ')' + (q.ring ? '<br>ring ' + q.ring : '');
    } else if (lk.kind === 'tree' || lk.kind === 'treeOther') {
      const child = treeParent(lk.band, lk.s, S.ep) === lk.a ? lk.s : lk.a;
      const t = treeTarget(lk.band, child, S.ep);
      html += ' of ' + esc(M.H.bands[lk.band].split(':')[1]) + (lk.both ? ' (both signals)' : '') + (t != null ? ', whole number ' + t : '');
    }
  }
  tip.innerHTML = html;
  tip.hidden = false;
  const pane = document.getElementById('graph-pane');
  tip.style.left = Math.min(x + 14, pane.clientWidth - 260) + 'px';
  tip.style.top = (y + 14) + 'px';
}

function wireControls() {
  const fam = document.getElementById('family');
  M.H.families.forEach((f, i) => fam.insertAdjacentHTML('beforeend', '<option value="' + i + '">' + esc(famLabel(f)) + (f.fixing ? ' (held)' : '') + '</option>'));
  fam.addEventListener('change', () => setFamily(+fam.value));
  document.getElementById('band').addEventListener('change', ev => { S.bandSel = +ev.target.value; TL.cache = null; drawGraph(); updateDetailNow(); saveHash(); });
  document.getElementById('layout').addEventListener('change', ev => { S.layout = ev.target.value; drawGraph(); saveHash(); });
  document.getElementById('show-float').addEventListener('change', ev => { S.showFloat = ev.target.checked; drawGraph(); });
  document.getElementById('show-held').addEventListener('change', ev => { S.showHeld = ev.target.checked; drawGraph(); });
  document.getElementById('show-labels').addEventListener('change', ev => { S.showLabels = ev.target.checked; drawGraph(); });
  const slider = document.getElementById('slider');
  slider.max = M.nEp - 1;
  slider.addEventListener('input', () => setEp(+slider.value));
  document.getElementById('play').addEventListener('click', play);
  document.getElementById('speed').addEventListener('change', ev => { S.speed = +ev.target.value; });
  const dl = document.getElementById('names');
  dl.innerHTML = M.names.map(n => '<option value="' + esc(n) + '">').join('');
  const search = document.getElementById('search');
  search.addEventListener('change', () => {
    const v = search.value.trim().toUpperCase();
    let n = M.nodeIndex.get(v);
    if (n == null) n = M.names.findIndex(x => x.toUpperCase().startsWith(v));
    if (n != null && n >= 0) selectNode(n);
  });
  document.getElementById('legend-btn').addEventListener('click', () => { document.getElementById('legend').hidden = false; });
  document.getElementById('legend-close').addEventListener('click', () => { document.getElementById('legend').hidden = true; });
  document.getElementById('legend').addEventListener('click', ev => { if (ev.target.id === 'legend') ev.target.hidden = true; });
  const cv = document.getElementById('graph');
  cv.addEventListener('mousemove', ev => {
    const r = cv.getBoundingClientRect();
    const hit = hitTest(ev.clientX - r.left, ev.clientY - r.top);
    const changed = JSON.stringify(hit && (hit.node != null ? hit.node : [hit.lk.a, hit.lk.s])) !== JSON.stringify(S.hover && (S.hover.node != null ? S.hover.node : [S.hover.lk.a, S.hover.lk.s]));
    S.hover = hit;
    showTooltip(hit, ev.clientX - r.left, ev.clientY - r.top);
    cv.style.cursor = hit ? 'pointer' : 'default';
    if (changed) drawGraph();
  });
  cv.addEventListener('mouseleave', () => { S.hover = null; showTooltip(null); drawGraph(); });
  cv.addEventListener('click', ev => {
    const r = cv.getBoundingClientRect();
    const hit = hitTest(ev.clientX - r.left, ev.clientY - r.top);
    if (!hit) { clearSelection(); return; }
    if (hit.kind === 'node') selectNode(hit.node);
    else selectLink(hit.lk.a, hit.lk.s - M.nSta);
  });
  const tl = document.getElementById('timeline');
  tl.addEventListener('click', ev => {
    const r = tl.getBoundingClientRect(), x = ev.clientX - r.left, y = ev.clientY - r.top;
    const lanes = timelineLanes(), k = Math.floor((y - TL.top) / TL.laneH);
    let e = tlEp(x, r.width);
    if (k >= 0 && k < lanes.length && x >= TL.labelW) {
      const c = lanes[k].counts, span = Math.max(2, Math.round(6 / (r.width - TL.labelW) * M.nEp));
      let best = -1;
      for (let d = 0; d <= span; d++) {
        if (e - d >= 0 && c[e - d]) { best = e - d; break; }
        if (e + d < M.nEp && c[e + d]) { best = e + d; break; }
      }
      if (best >= 0) {
        e = best;
        setEp(e);
        if (!lanes[k].selected) { S.sel = { kind: 'events', ep: e, lane: lanes[k].lane }; TL.cache = null; renderDetail(); drawTimeline(); }
        return;
      }
    }
    setEp(e);
  });
  tl.addEventListener('mousemove', ev => {
    const r = tl.getBoundingClientRect(), x = ev.clientX - r.left, y = ev.clientY - r.top;
    const lanes = timelineLanes(), k = Math.floor((y - TL.top) / TL.laneH), e = tlEp(x, r.width);
    tl.title = clockOf(e) + (k >= 0 && k < lanes.length ? '  ' + lanes[k].label + ': ' + lanes[k].counts[e] + ' at this epoch' : '');
  });
  document.addEventListener('keydown', ev => {
    if (ev.target.tagName === 'INPUT' && ev.target.type !== 'range' || ev.target.tagName === 'SELECT') return;
    if (ev.key === 'ArrowRight') { setEp(S.ep + (ev.shiftKey ? 10 : 1)); ev.preventDefault(); }
    else if (ev.key === 'ArrowLeft') { setEp(S.ep - (ev.shiftKey ? 10 : 1)); ev.preventDefault(); }
    else if (ev.key === ' ') { play(); ev.preventDefault(); }
    else if (ev.key === 'Home') setEp(0);
    else if (ev.key === 'End') setEp(M.nEp - 1);
    else if (ev.key === 'Escape') { if (!document.getElementById('legend').hidden) document.getElementById('legend').hidden = true; else clearSelection(); }
  });
  let rt = null;
  window.addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(() => { fitMain(); TL.cache = null; for (const c of CHARTS) c.img = null; drawGraph(); drawTimeline(); drawAllCharts(); }, 120); });
  const mq = window.matchMedia('(prefers-color-scheme: dark)');
  if (mq.addEventListener) mq.addEventListener('change', () => { readColors(); TL.cache = null; renderDetail(); renderSummary(); drawGraph(); drawTimeline(); });
}

/** The network and the detail panel fill the window below the time bar (the summaries follow below). */
function fitMain() {
  const main = document.getElementById('main');
  if (window.matchMedia('(max-width: 760px)').matches) { main.style.height = ''; return; }
  const top = main.getBoundingClientRect().top + window.scrollY;
  const h = Math.max(520, window.innerHeight - top - 6);
  main.style.height = h + 'px';
  document.getElementById('detail').style.maxHeight = h + 'px';
}

function defaultFamily() {
  const H = M.H;
  let best = -1, bestN = -1;
  H.families.forEach((f, i) => { if (f.held_link_epochs > bestN) { bestN = f.held_link_epochs; best = i; } });
  return best >= 0 ? best : 0;
}

async function start() {
  const t0 = performance.now();
  const { H, A } = await decodeBlock();
  buildModel(H, A);
  readColors();
  S.fam = defaultFamily();
  loadHash();
  document.getElementById('run-name').textContent = 'Network view: ' + H.run;
  const d = gpsDate(0);
  document.getElementById('run-sub').textContent = d.toISOString().slice(0, 10) + ' (day ' + dayOfYear(d) + '), ' +
    M.nSta + ' receivers, ' + M.nSat + ' satellites, ' + durationText(M.nEp) + '; built ' + H.built;
  document.getElementById('loading').hidden = true;
  document.getElementById('app').hidden = false;
  wireControls();
  document.getElementById('family').value = S.fam;
  document.getElementById('layout').value = S.layout;
  if (!M.nFam) for (const id of ['family', 'band']) document.getElementById(id).parentElement.hidden = true;
  fillBandSelect();
  renderLegend();
  renderMissing();
  drawTimeline();
  fitMain();
  document.getElementById('slider').value = S.ep;
  renderDetail();
  renderSummary();
  refreshTime();
  window.NV = { M, S, G };                    // for the comparison page and for checks from the console
  window.NV_OPEN_MS = Math.round(performance.now() - t0);
  console.log('network view opened in ' + window.NV_OPEN_MS + ' ms');
}

// A failure is shown on the page, never silent: the note names the message for a report.
window.addEventListener('error', ev => {
  const box = document.getElementById('missing');
  if (!box) return;
  box.hidden = false;
  box.insertAdjacentHTML('beforeend', '<div style="color:var(--release)">Something on this page failed: ' +
    esc(ev.message || String(ev.error)) + '. The rest of the page still works.</div>');
});

start().catch(err => {
  document.getElementById('loading').textContent = 'The page could not open its data: ' + err.message;
  console.error(err);
});
