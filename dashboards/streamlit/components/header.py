"""Finance Dashboard — Scrolling Market Ticker Header (live JS component)."""
from __future__ import annotations

import json

import streamlit as st
import streamlit.components.v1 as components

from config import API_URL
from utils.api import fetch_parallel, to_float

_CSS = (
    "<style>"
    ".qvt-wrapper{"
    "position:relative;overflow:hidden;"
    "background:linear-gradient(135deg,#0d1424 0%,#0f1a2e 100%);"
    "border:1px solid rgba(255,255,255,0.05);border-radius:10px;"
    "height:54px;display:flex;align-items:center;margin-bottom:1.2rem;"
    "}"
    ".qvt-live{"
    "flex-shrink:0;display:flex;align-items:center;gap:6px;"
    "padding:0 1.1rem 0 1rem;border-right:1px solid rgba(255,255,255,0.07);z-index:3;"
    "}"
    ".qvt-live-dot{"
    "width:6px;height:6px;border-radius:50%;background:#ef4444;flex-shrink:0;"
    "animation:qvt-dot 1.2s ease-in-out infinite;"
    "}"
    "@keyframes qvt-dot{"
    "0%,100%{opacity:1;box-shadow:0 0 6px #ef4444,0 0 12px rgba(239,68,68,0.4);}"
    "50%{opacity:0.12;box-shadow:none;}"
    "}"
    ".qvt-live-txt{"
    "font-size:0.53rem;font-weight:800;color:#ef4444;"
    "text-transform:uppercase;letter-spacing:0.2em;font-family:Inter,sans-serif;"
    "}"
    ".qvt-scroll{"
    "flex:1;overflow:hidden;position:relative;"
    "}"
    ".qvt-scroll::before,.qvt-scroll::after{"
    "content:'';position:absolute;top:0;bottom:0;width:48px;z-index:2;pointer-events:none;"
    "}"
    ".qvt-scroll::before{left:0;background:linear-gradient(to right,#0d1424 30%,transparent);}"
    ".qvt-scroll::after{right:0;background:linear-gradient(to left,#0d1424 30%,transparent);}"
    ".qvt-track{"
    "display:inline-flex;white-space:nowrap;align-items:center;"
    "animation:qvt-run 40s linear infinite;"
    "}"
    ".qvt-track:hover{animation-play-state:paused;}"
    "@keyframes qvt-run{"
    "0%{transform:translateX(0);}100%{transform:translateX(-50%);}"
    "}"
    ".qvt-item{display:inline-flex;align-items:center;gap:6px;padding:0 2rem;}"
    ".qvt-lbl{"
    "font-size:0.55rem;font-weight:700;text-transform:uppercase;"
    "letter-spacing:0.13em;color:#94a3b8;font-family:Inter,sans-serif;"
    "}"
    ".qvt-val{"
    "font-size:0.88rem;font-weight:700;font-family:'JetBrains Mono',monospace;"
    "}"
    ".qvt-dlt{"
    "font-size:0.65rem;font-weight:600;font-family:'JetBrains Mono',monospace;"
    "}"
    ".qvt-sep{color:rgba(255,255,255,0.18);font-size:0.85rem;margin-left:0.5rem;}"
    ".qvt-pos{color:#10b981;animation:qvt-p 2.4s ease-in-out infinite;}"
    ".qvt-neg{color:#ef4444;animation:qvt-n 2.4s ease-in-out infinite;}"
    ".qvt-neu{color:#94a3b8;animation:qvt-u 3s ease-in-out infinite;}"
    "@keyframes qvt-p{"
    "0%,100%{color:#10b981;text-shadow:none;}"
    "50%{color:#34d399;text-shadow:0 0 10px rgba(16,185,129,0.75);}"
    "}"
    "@keyframes qvt-n{"
    "0%,100%{color:#ef4444;text-shadow:none;}"
    "50%{color:#f87171;text-shadow:0 0 10px rgba(239,68,68,0.75);}"
    "}"
    "@keyframes qvt-u{"
    "0%,100%{color:#94a3b8;}"
    "50%{color:#cbd5e1;}"
    "}"
    "</style>"
)


def _item(label: str, value: str, delta: str, cls: str) -> str:
    return (
        f"<span class='qvt-item'>"
        f"<span class='qvt-lbl'>{label}</span>"
        f"<span class='qvt-val {cls}'>{value}</span>"
        f"<span class='qvt-dlt {cls}'>{delta}</span>"
        f"<span class='qvt-sep'>|</span>"
        f"</span>"
    )


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_header_data() -> dict:
    """Fetch all header data with a 60-second cache to avoid re-fetching on every rerun."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from utils import direct as d

    selic_data, ipca_data, cambio_data = fetch_parallel(
        [
            ("/macro/brasil/selic", None),
            ("/macro/brasil/ipca", None),
            ("/macro/brasil/cambio_dolar", None),
        ],
        timeout=8,
    )

    # Fetch market quotes in parallel to avoid sequential blocking
    _symbols = {"ibov": "^BVSP", "btc": "BTC-USD", "sp500": "^GSPC", "eur": "EURUSD=X"}
    quotes: dict = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(d.market_quote, sym): key for key, sym in _symbols.items()}
        try:
            for future in as_completed(futures, timeout=12):
                try:
                    quotes[futures[future]] = future.result()
                except Exception:
                    pass
        except TimeoutError:
            for future, key in futures.items():
                if future.done():
                    try:
                        quotes[key] = future.result()
                    except Exception:
                        pass

    return {
        "selic":  selic_data,
        "ipca":   ipca_data,
        "cambio": cambio_data,
        "ibov":   quotes.get("ibov"),
        "btc":    quotes.get("btc"),
        "sp500":  quotes.get("sp500"),
        "eur":    quotes.get("eur"),
    }


def render_header() -> None:
    """Render the scrolling market ticker header."""
    data = _fetch_header_data()

    selic_data  = data["selic"]
    ipca_data   = data["ipca"]
    cambio_data = data["cambio"]

    def _last_two(series: list | None) -> tuple[float | None, float | None]:
        if not series or not isinstance(series, list):
            return None, None
        last = to_float(series[-1].get("valor"))
        prev = to_float(series[-2].get("valor")) if len(series) >= 2 else None
        return last, prev

    def _build(last: float | None, prev: float | None, fmt: str, suffix: str,
               inverse: bool = False) -> tuple[str, str, str]:
        val_str = f"{last:{fmt}}{suffix}" if last is not None else "—"
        if last is not None and prev is not None:
            diff = last - prev
            sign = "+" if diff >= 0 else ""
            good = (diff >= 0) if not inverse else (diff < 0)
            cls = "qvt-pos" if good else "qvt-neg"
            delta_str = f"{sign}{diff:{fmt}}{suffix}"
        else:
            cls = "qvt-neu"
            delta_str = "—"
        return val_str, delta_str, cls

    selic_l, selic_p   = _last_two(selic_data)
    ipca_l,  ipca_p    = _last_two(ipca_data)
    cambio_l, cambio_p = _last_two(cambio_data)

    selic_v,  selic_d,  selic_c  = _build(selic_l,  selic_p,  ".2f", "%")
    ipca_v,   ipca_d,   ipca_c   = _build(ipca_l,   ipca_p,   ".2f", "%", inverse=True)
    cambio_v, cambio_d, cambio_c = _build(cambio_l,  cambio_p, ".4f", "", inverse=True)

    def _quote(label: str, q: dict | None, fmt: str = ",.2f", prefix: str = "") -> str:
        if q:
            v   = f"{prefix}{q['last']:{fmt}}"
            pct = q["chg_pct"]
            sign = "+" if pct >= 0 else ""
            cls  = "qvt-pos" if pct >= 0 else "qvt-neg"
            return _item(label, v, f"{sign}{pct:.2f}%", cls)
        return _item(label, "—", "—", "qvt-neu")

    # ── JS component: auto-refreshes macro values every 60 s without page rerun
    _JS_REFRESH = f"""
<script>
(function(){{
  const API = {json.dumps(API_URL)};
  const INTERVAL_MS = 60000;

  function _last2(arr) {{
    if (!arr || arr.length < 1) return [null, null];
    return [parseFloat(arr[arr.length-1].valor), arr.length >= 2 ? parseFloat(arr[arr.length-2].valor) : null];
  }}

  function _fmtDelta(last, prev, fmt, inverse) {{
    if (last == null || prev == null) return {{val: "—", delta: "—", cls: "qvt-neu"}};
    const diff = last - prev;
    const good = inverse ? diff < 0 : diff >= 0;
    return {{
      val: last.toFixed(fmt) + (fmt <= 2 ? "%" : ""),
      delta: (diff >= 0 ? "+" : "") + diff.toFixed(fmt) + (fmt <= 2 ? "%" : ""),
      cls: good ? "qvt-pos" : "qvt-neg"
    }};
  }}

  function _updateItem(id, info) {{
    const el = document.getElementById(id);
    if (!el) return;
    el.querySelector(".qvt-val").textContent  = info.val;
    el.querySelector(".qvt-dlt").textContent  = info.delta;
    el.querySelector(".qvt-val").className    = "qvt-val " + info.cls;
    el.querySelector(".qvt-dlt").className    = "qvt-dlt " + info.cls;
  }}

  async function refresh() {{
    try {{
      const [sr, ir, cr] = await Promise.all([
        fetch(API + "/macro/brasil/selic",        {{signal: AbortSignal.timeout(5000)}}),
        fetch(API + "/macro/brasil/ipca",         {{signal: AbortSignal.timeout(5000)}}),
        fetch(API + "/macro/brasil/cambio_dolar", {{signal: AbortSignal.timeout(5000)}}),
      ]);
      if (!sr.ok) return;
      const [selic, ipca, cambio] = await Promise.all([sr.json(), ir.json(), cr.json()]);
      const [sl, sp] = _last2(selic);
      const [il, ip] = _last2(ipca);
      const [cl, cp] = _last2(cambio);
      _updateItem("qvt-selic",  _fmtDelta(sl, sp, 2, false));
      _updateItem("qvt-ipca",   _fmtDelta(il, ip, 2, true));
      _updateItem("qvt-cambio", {{val: cl != null ? cl.toFixed(4) : "—",
                                  delta: (cp != null && cl != null)
                                    ? (cl-cp >= 0 ? "+" : "") + (cl-cp).toFixed(4) : "—",
                                  cls: (cl != null && cp != null && cl < cp) ? "qvt-pos" : "qvt-neg"}});
    }} catch(e) {{/* offline — keep showing current values */}}
  }}

  setInterval(refresh, INTERVAL_MS);
}})();
</script>
"""

    # Build item HTML with unique IDs so JS can update values in-place
    def _item_live(id_: str, label: str, val: str, delta: str, cls: str) -> str:
        return (
            f"<span id='{id_}' class='qvt-item'>"
            f"<span class='qvt-lbl'>{label}</span>"
            f"<span class='qvt-val {cls}'>{val}</span>"
            f"<span class='qvt-dlt {cls}'>{delta}</span>"
            f"<span class='qvt-sep'>|</span>"
            f"</span>"
        )

    live_items = (
        _item_live("qvt-selic",  "SELIC",     selic_v,  selic_d,  selic_c)   +
        _item_live("qvt-ipca",   "IPCA 12m",  ipca_v,   ipca_d,   ipca_c)    +
        _item_live("qvt-cambio", "USD / BRL", cambio_v, cambio_d, cambio_c)  +
        _quote("IBOVESPA",  data["ibov"],  fmt=",.0f")                         +
        _quote("BTC / USD", data["btc"],   fmt=",.0f", prefix="$")             +
        _quote("S&P 500",   data["sp500"], fmt=",.2f")                         +
        _quote("EUR / USD", data["eur"],   fmt=".4f")
    )

    full_html = (
        _CSS
        + "<div class='qvt-wrapper'>"
        + "<div class='qvt-live'>"
        + "<span class='qvt-live-dot'></span>"
        + "<span class='qvt-live-txt'>AO VIVO</span>"
        + "</div>"
        + "<div class='qvt-scroll'>"
        + f"<div class='qvt-track'>{live_items}{live_items}</div>"
        + "</div>"
        + "</div>"
        + _JS_REFRESH
    )

    components.html(full_html, height=70, scrolling=False)
