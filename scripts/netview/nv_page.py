"""Writes the page: one HTML file that opens from file:// with no server and no network access.

The data block is a small binary container, gzip-compressed and base64-encoded into a script tag:
    'NVB1' | u32 header length | header JSON (UTF-8) | padding to 8 | arrays, each aligned to 8 bytes
The page decompresses it with the browser's DecompressionStream and takes typed-array views of the arrays
(little-endian, as numpy writes them on x86), so nothing large is parsed as text.

The page's script, style and markup live beside this file in page/ and are inlined here.  The colour maps are the
viridis (magnitudes) and vik (signed values) anchor tables of pyviz/gnssviz/colormaps.py.
"""
from __future__ import annotations

import base64
import gzip
import importlib.util
import json
import math
import os
import re
import struct
import urllib.parse
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

#: numpy dtype -> name of the JavaScript typed array that views it.
JS_TYPES = {
    np.dtype('int8'): 'Int8Array', np.dtype('uint8'): 'Uint8Array', np.dtype('int16'): 'Int16Array',
    np.dtype('uint16'): 'Uint16Array', np.dtype('int32'): 'Int32Array', np.dtype('uint32'): 'Uint32Array',
    np.dtype('float32'): 'Float32Array', np.dtype('float64'): 'Float64Array',
}


def _clean(v):
    """JSON-safe copy of a header value: NaN and infinities become null, numpy scalars plain numbers."""
    if isinstance(v, dict):
        return {str(k): _clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v]
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        return float(v) if math.isfinite(v) else None
    return v


def pack(header: dict, arrays: dict) -> bytes:
    """The binary container of the block (uncompressed)."""
    entries, blobs = [], bytearray()
    for name, a in arrays.items():
        a = np.ascontiguousarray(a)
        if a.dtype == np.int64:
            a = a.astype(np.int32)
        if a.dtype not in JS_TYPES:
            raise TypeError(f'array {name}: dtype {a.dtype} has no typed-array view')
        blobs += b'\0' * ((-len(blobs)) % 8)
        entries.append({'name': name, 'type': JS_TYPES[a.dtype], 'shape': list(a.shape), 'offset': len(blobs),
                        'length': int(a.size)})
        blobs += a.astype(a.dtype.newbyteorder('<'), copy=False).tobytes()
    head = dict(header)
    head['arrays'] = entries
    hj = json.dumps(_clean(head), separators=(',', ':'), allow_nan=False, ensure_ascii=False).encode('utf-8')
    out = bytearray(b'NVB1' + struct.pack('<I', len(hj)) + hj)
    out += b'\0' * ((-len(out)) % 8)
    return bytes(out + blobs)


def colormaps():
    """viridis and vik anchor tables from pyviz/gnssviz/colormaps.py (loaded by path: the package's __init__ pulls
    in its viewers, which this tool does not need)."""
    p = REPO / 'pyviz' / 'gnssviz' / 'colormaps.py'
    spec = importlib.util.spec_from_file_location('nv_colormaps', p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {'viridis': np.round(mod._VIRIDIS, 4).tolist(), 'vik': np.round(mod._VIK, 4).tolist()}


def coastline():
    """The vendored Natural Earth 1:110m coastline of pyviz (public domain), rounded to 0.1 degree."""
    p = REPO / 'pyviz' / 'gnssviz' / 'assets' / 'coastline_110m.json'
    if not p.exists():
        return None
    j = json.loads(p.read_text(encoding='utf-8'))
    r = lambda v: None if v is None else round(v, 1)                       # noqa: E731
    return {'lon': [r(v) for v in j['lon']], 'lat': [r(v) for v in j['lat']]}


def write_page(path: Path, header: dict, arrays: dict, compress: bool = True) -> dict:
    """Write the HTML file; returns sizes (bytes) of the raw block, the encoded block and the page."""
    raw = pack(header, arrays)
    data = gzip.compress(raw, compresslevel=6, mtime=0) if compress else raw
    b64 = base64.b64encode(data).decode('ascii')
    page = (HERE / 'page' / 'netview.html').read_text(encoding='utf-8')
    css = (HERE / 'page' / 'netview.css').read_text(encoding='utf-8')
    js = (HERE / 'page' / 'netview.js').read_text(encoding='utf-8')
    assets = json.dumps({'colormaps': colormaps(), 'coastline': coastline()}, separators=(',', ':'))
    fill = {'CSS': css, 'ASSETS': f'window.NV_ASSETS = {assets};', 'JS': js,
            'TITLE': _html_escape(f'Network view {header.get("run", "")}'),
            'ENCODING': 'gzip' if compress else 'raw', 'DATA': b64}
    # one pass over the template only, so text inserted for one token is never scanned for another
    html = re.sub(r'\{\{(CSS|ASSETS|JS|TITLE|ENCODING|DATA)\}\}', lambda m: fill[m.group(1)], page)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding='utf-8', newline='\n')
    return {'raw': len(raw), 'encoded': len(b64), 'page': path.stat().st_size}


def _html_escape(s: str) -> str:
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


COMPARE_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Network view comparison</title>
<style>
  :root { color-scheme: light dark; }
  html, body { margin: 0; height: 100%; background: #fbfbf9; font: 13px system-ui, sans-serif; }
  @media (prefers-color-scheme: dark) { html, body { background: #171716; color: #e9e8e3; } }
  .bar { padding: 4px 12px; color: #6b6b66; }
  .wrap { display: flex; height: calc(100vh - 26px); }
  iframe { flex: 1; min-width: 0; height: 100%; border: 0; border-left: 2px solid #d9d8d2; }
  iframe:first-child { border-left: 0; }
  @media (max-width: 900px) { .wrap { flex-direction: column; height: auto; } iframe { height: 100vh; border-left: 0; } }
</style>
</head>
<body>
<div class="bar">Left: {{A_NAME}} &nbsp;|&nbsp; right: {{B_NAME}}. Time, signals, layout and the selected link or node follow
each other; each side keeps its own tree.</div>
<div class="wrap">
  <iframe id="a" src="{{A_SRC}}" title="{{A_NAME}}"></iframe>
  <iframe id="b" src="{{B_SRC}}" title="{{B_NAME}}"></iframe>
</div>
<script>
  const frames = [document.getElementById('a'), document.getElementById('b')];
  window.addEventListener('message', ev => {
    if (!ev.data || ev.data.nv !== 'sync') return;
    for (const f of frames) if (f.contentWindow !== ev.source) f.contentWindow.postMessage(ev.data, '*');
  });
</script>
</body>
</html>
"""


def write_compare(path: Path, page_a: Path, page_b: Path) -> None:
    """A page that shows two network view pages side by side with their time and selection linked."""
    def src(p: Path) -> str:
        rel = Path(os.path.relpath(p.resolve(), path.resolve().parent)).as_posix()
        return urllib.parse.quote(rel)

    fill = {'A_SRC': src(page_a), 'B_SRC': src(page_b), 'A_NAME': _html_escape(page_a.stem),
            'B_NAME': _html_escape(page_b.stem)}
    html = re.sub(r'\{\{(A_SRC|B_SRC|A_NAME|B_NAME)\}\}', lambda m: fill[m.group(1)], COMPARE_PAGE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding='utf-8', newline='\n')
