"""Finance Charts — Reusable Chart Utilities."""
from __future__ import annotations

import math
import random
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .styles import (
    BG_CARD, BG_CARD2, BORDER, BORDER_LIGHT,
    C_NEG, C_NEG2, C_NEUT, C_NEUT2, C_POS, C_POS2, C_WARN, C_PURPLE,
    TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY,
    PALETTE, base_layout,
)


# ── KPI Cards ─────────────────────────────────────────────────────────────────

def kpi_card(
    label: str,
    value: str,
    delta: str = "",
    delta_positive: bool | None = None,
    accent: str = C_NEUT,
    icon: str = "",
    sparkline: list[float] | None = None,
) -> str:
    delta_color = (C_POS if delta_positive else C_NEG) if delta_positive is not None else TEXT_SECONDARY
    arrow = ("▲ " if delta_positive else "▼ ") if delta_positive is not None else ""
    spark_html = _sparkline_svg(sparkline, accent) if sparkline else ""
    return (
        f"<div style='background:{BG_CARD};border:1px solid {BORDER};"
        f"border-top:2px solid {accent};border-radius:10px;"
        f"padding:1rem 1.1rem;position:relative;overflow:hidden;'>"
        f"<div style='font-size:0.62rem;font-weight:700;text-transform:uppercase;"
        f"letter-spacing:0.1em;color:{TEXT_MUTED};font-family:Inter,sans-serif;"
        f"margin-bottom:0.35rem;'>{icon} {label}</div>"
        f"<div style='font-size:1.45rem;font-weight:800;color:{TEXT_PRIMARY};"
        f"font-family:\"JetBrains Mono\",monospace;letter-spacing:-0.02em;"
        f"line-height:1.15;'>{value}</div>"
        f"<div style='font-size:0.72rem;font-weight:600;color:{delta_color};"
        f"font-family:\"JetBrains Mono\",monospace;margin-top:0.25rem;'>"
        f"{arrow}{delta}</div>"
        f"{spark_html}"
        f"</div>"
    )


def _sparkline_svg(data: list[float], color: str = C_NEUT, width: int = 80, height: int = 26) -> str:
    if not data or len(data) < 2:
        return ""
    mn, mx = min(data), max(data)
    rng = mx - mn or 1
    pts = []
    for i, v in enumerate(data):
        x = int(i / (len(data) - 1) * width)
        y = int((1 - (v - mn) / rng) * height)
        pts.append(f"{x},{y}")
    path = "M" + " L".join(pts)
    return (
        f"<div style='position:absolute;bottom:8px;right:8px;opacity:0.55;'>"
        f"<svg width='{width}' height='{height}' fill='none'>"
        f"<polyline points='{' '.join(pts)}' stroke='{color}' stroke-width='1.5' fill='none'/>"
        f"</svg></div>"
    )


# ── Insight Box ───────────────────────────────────────────────────────────────

def insight_box(text: str, color: str = C_NEUT, icon: str = "◆") -> None:
    st.markdown(
        f"<div style='background:rgba(59,130,246,0.04);border-left:3px solid {color};"
        f"border-radius:0 8px 8px 0;padding:0.75rem 1rem;margin-top:0.5rem;"
        f"font-size:0.82rem;color:{TEXT_SECONDARY};font-family:Inter,sans-serif;line-height:1.6;'>"
        f"<span style='color:{color};font-weight:700;'>{icon} Análise: </span>{text}"
        f"</div>",
        unsafe_allow_html=True,
    )


def section_header_charts(title: str, subtitle: str = "", color: str = C_NEUT) -> None:
    sub_html = (
        f"<div style='font-size:0.72rem;color:{TEXT_MUTED};margin-top:2px;"
        f"font-family:Inter,sans-serif;'>{subtitle}</div>"
        if subtitle else ""
    )
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:10px;"
        f"margin-bottom:0.75rem;padding-bottom:0.6rem;"
        f"border-bottom:1px solid {BORDER};'>"
        f"<div style='width:6px;height:6px;border-radius:50%;background:{color};"
        f"box-shadow:0 0 10px {color};flex-shrink:0;'></div>"
        f"<div>"
        f"<span style='font-size:0.88rem;font-weight:700;color:{TEXT_PRIMARY};"
        f"text-transform:uppercase;letter-spacing:0.06em;font-family:Inter,sans-serif;'>"
        f"{title}</span>"
        f"{sub_html}"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


# ── Data Generators (for demo when API is unavailable) ───────────────────────

def _seed(ticker: str) -> int:
    return sum(ord(c) for c in ticker)


def make_quarterly_df(ticker: str, n: int = 16) -> pd.DataFrame:
    rng = random.Random(_seed(ticker))
    dates = pd.date_range(end=pd.Timestamp.today(), periods=n, freq="QE")
    receita = [rng.uniform(3_000, 12_000) for _ in range(n)]
    ebitda  = [r * rng.uniform(0.28, 0.48) for r in receita]
    lucro   = [e * rng.uniform(0.45, 0.80) for e in ebitda]
    return pd.DataFrame({
        "data": dates,
        "receita": receita,
        "ebitda": ebitda,
        "lucro_liquido": lucro,
        "margem_liquida": [l / r * 100 for l, r in zip(lucro, receita)],
        "margem_ebitda":  [e / r * 100 for e, r in zip(ebitda, receita)],
    })


def make_annual_df(ticker: str, n: int = 8) -> pd.DataFrame:
    rng = random.Random(_seed(ticker) + 1)
    years = list(range(2017, 2017 + n))
    receita = [rng.uniform(10_000, 50_000) for _ in range(n)]
    ebitda  = [r * rng.uniform(0.30, 0.50) for r in receita]
    lucro   = [e * rng.uniform(0.40, 0.78) for e in ebitda]
    div_bruta = [rng.uniform(5_000, 25_000) for _ in range(n)]
    patrimonio = [rng.uniform(8_000, 30_000) for _ in range(n)]
    div_liquida = [db * rng.uniform(0.5, 0.9) - p * 0.1 for db, p in zip(div_bruta, patrimonio)]
    return pd.DataFrame({
        "ano": years,
        "receita": receita,
        "ebitda": ebitda,
        "lucro_liquido": lucro,
        "margem_liquida": [l / r * 100 for l, r in zip(lucro, receita)],
        "margem_ebitda":  [e / r * 100 for e, r in zip(ebitda, receita)],
        "divida_bruta": div_bruta,
        "divida_liquida": div_liquida,
        "patrimonio_liquido": patrimonio,
        "alavancagem": [dl / e for dl, e in zip(div_liquida, ebitda)],
    })


def make_dividends_df(ticker: str, n: int = 20) -> pd.DataFrame:
    rng = random.Random(_seed(ticker) + 2)
    dates = pd.date_range(end=pd.Timestamp.today(), periods=n, freq="QE")
    dividends = [rng.uniform(0.05, 1.20) for _ in range(n)]
    prices    = [rng.uniform(15, 60) for _ in range(n)]
    return pd.DataFrame({
        "data": dates,
        "dividendo": dividends,
        "preco": prices,
        "yield_trimestral": [d / p * 100 for d, p in zip(dividends, prices)],
    })


# ── Color Helpers ─────────────────────────────────────────────────────────────

def _fmt_brl(val: float) -> str:
    av = abs(val)
    if av >= 1e12:
        return f"R$ {val/1e12:.2f}T"
    if av >= 1e9:
        return f"R$ {val/1e9:.2f}B"
    if av >= 1e6:
        return f"R$ {val/1e6:.2f}M"
    if av >= 1e3:
        return f"R$ {val/1e3:.2f}K"
    return f"R$ {val:.2f}"


def _chart_scale(values: list[float]) -> tuple[float, str]:
    mx = max((abs(v) for v in values if v is not None), default=1.0)
    if mx >= 1e12:
        return 1e12, "T"
    if mx >= 1e9:
        return 1e9, "B"
    if mx >= 1e6:
        return 1e6, "M"
    if mx >= 1e3:
        return 1e3, "K"
    return 1.0, ""


def color_pos_neg(value: float, neutral_zero: bool = False) -> str:
    if neutral_zero and abs(value) < 0.001:
        return C_NEUT2
    return C_POS if value >= 0 else C_NEG


def leverage_color(ratio: float) -> str:
    if ratio <= 1.5:
        return C_POS
    if ratio <= 3.0:
        return C_WARN
    return C_NEG


def valuation_color(value: float, mean: float, std: float) -> str:
    if value < mean - std:
        return C_POS
    if value > mean + std:
        return C_NEG
    return C_WARN


# ── Glow-Line Trace ───────────────────────────────────────────────────────────

def glow_line_trace(
    x: Any,
    y: Any,
    name: str,
    color: str = C_NEUT,
    width: float = 2.5,
    fill: bool = True,
    fill_opacity: float = 0.08,
    dash: str = "solid",
    mode: str = "lines",
) -> list[go.BaseTraceType]:
    r, g, b = _hex_to_rgb(color)
    traces: list[go.BaseTraceType] = []

    if fill:
        traces.append(go.Scatter(
            x=x, y=y, mode="lines",
            line=dict(color=f"rgba({r},{g},{b},0)", width=0),
            fill="tozeroy",
            fillcolor=f"rgba({r},{g},{b},{fill_opacity})",
            showlegend=False, hoverinfo="skip",
        ))

    traces.append(go.Scatter(
        x=x, y=y, name=name, mode=mode,
        line=dict(color=color, width=width, dash=dash, shape="spline", smoothing=0.4),
        marker=dict(color=color, size=5, opacity=0) if "markers" in mode else dict(),
        hovertemplate=f"<b>{name}</b><br>%{{y:.2f}}<extra></extra>",
    ))
    return traces


def _generate_price_history(ticker: str, n: int = 252) -> pd.DataFrame:
    rng    = random.Random(_seed(ticker) + 10)
    np_rng = np.random.RandomState(_seed(ticker))
    price  = rng.uniform(15, 70)
    prices = [price]
    for _ in range(n - 1):
        ret = np_rng.normal(0.0004, 0.018)
        prices.append(prices[-1] * (1 + ret))
    dates = pd.date_range(end=pd.Timestamp.today(), periods=n, freq="B")
    return pd.DataFrame({"data": dates, "fechamento": prices})


def hex_alpha(color: str, alpha: float) -> str:
    """Convert '#RRGGBB' + float alpha to 'rgba(R,G,B,A)' for Plotly."""
    r, g, b = _hex_to_rgb(color)
    return f"rgba({r},{g},{b},{alpha:.2f})"


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    c = color.lstrip("#")
    if len(c) == 3:
        c = "".join(x * 2 for x in c)
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
