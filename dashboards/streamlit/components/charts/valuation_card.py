"""Finance Charts — Painel de Valuation Simplificado (Equity Research Style)."""
from __future__ import annotations

import random
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .styles import (
    BG_CARD, BG_CARD2, BORDER, BORDER_LIGHT, C_NEG, C_NEUT, C_NEUT2,
    C_POS, C_POS2, C_WARN, C_PURPLE, C_CYAN,
    TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY, base_layout,
)
from .utils import (
    insight_box, kpi_card, section_header_charts, _seed,
)


def _valuation_score(pl: float, roe: float, dy: float, pl_sector: float) -> tuple[float, str, str]:
    score = 50.0
    if pl < pl_sector * 0.8:
        score += 20
    elif pl > pl_sector * 1.3:
        score -= 20
    if roe > 20:
        score += 15
    elif roe > 12:
        score += 8
    else:
        score -= 10
    if dy > 6:
        score += 10
    elif dy > 3:
        score += 5

    score = max(0.0, min(100.0, score))

    if score >= 65:
        return score, "Subvalorizada", C_POS
    if score >= 40:
        return score, "Neutra", C_WARN
    return score, "Sobrevalorizada", C_NEG


def _metric_row(label: str, value: str, note: str = "", color: str = TEXT_SECONDARY) -> str:
    return (
        f"<div style='display:flex;justify-content:space-between;align-items:center;"
        f"padding:0.5rem 0;border-bottom:1px solid rgba(255,255,255,0.04);'>"
        f"<span style='font-size:0.8rem;color:{TEXT_MUTED};font-family:Inter,sans-serif;'>{label}</span>"
        f"<div style='display:flex;align-items:center;gap:10px;'>"
        f"<span style='font-size:0.88rem;font-weight:700;color:{color};"
        f"font-family:\"JetBrains Mono\",monospace;'>{value}</span>"
        f"<span style='font-size:0.68rem;color:{TEXT_MUTED};font-family:Inter,sans-serif;'>{note}</span>"
        f"</div>"
        f"</div>"
    )


def _generate_valuation_data(ticker: str) -> dict:
    rng = random.Random(_seed(ticker) + 7)
    preco  = rng.uniform(10, 80)
    lpa    = rng.uniform(1.5, 8.0)
    pl     = preco / lpa
    vpa    = rng.uniform(8, 40)
    pvp    = preco / vpa
    ebitda = rng.uniform(3, 15) * 1e9
    ev     = ebitda * rng.uniform(4, 12)
    ev_ebitda = ev / ebitda
    roe    = rng.uniform(8, 35)
    roic   = rng.uniform(6, 28)
    dy     = rng.uniform(2, 12)
    payout = rng.uniform(30, 90)
    div_liq_ebitda = rng.uniform(0.5, 4.0)
    pat_liq = rng.uniform(5e9, 50e9)
    lucro_proj = lpa * rng.uniform(0.9, 1.2) * 1e8
    return {
        "preco": preco, "lpa": lpa, "pl": pl,
        "vpa": vpa, "pvp": pvp,
        "ev_ebitda": ev_ebitda, "roe": roe, "roic": roic,
        "dy": dy, "payout": payout,
        "div_liq_ebitda": div_liq_ebitda,
        "pat_liq": pat_liq, "lucro_proj": lucro_proj,
        "pl_setor": rng.uniform(8, 16),
    }


def render_valuation_card(
    data: dict | None = None,
    ticker: str = "TICKER",
    sector: str = "Setor",
) -> None:
    if data is None:
        data = _generate_valuation_data(ticker)

    # Normalise: ensure all required keys exist so real-API dicts don't crash
    data = {
        "preco":          float(data.get("preco") or 0),
        "lpa":            float(data.get("lpa") or 0),
        "pl":             float(data.get("pl") or 12),
        "vpa":            float(data.get("vpa") or 0),
        "pvp":            float(data.get("pvp") or 1.5),
        "ev_ebitda":      float(data.get("ev_ebitda") or 8),
        "roe":            float(data.get("roe") or 12),
        "roic":           float(data.get("roic") or data.get("roe") or 10),
        "dy":             float(data.get("dy") or 3),
        "payout":         float(data.get("payout") or 40),
        "div_liq_ebitda": float(data.get("div_liq_ebitda") or 2),
        "pat_liq":        float(data.get("pat_liq") or 0),
        "lucro_proj":     float(data.get("lucro_proj") or 0),
        "pl_setor":       float(data.get("pl_setor") or 12),
        "nome":           data.get("nome", ticker),
    }

    score, classification, cls_color = _valuation_score(
        data["pl"], data["roe"], data["dy"], data.get("pl_setor", 12)
    )

    section_header_charts("Valuation — Visão Simplificada", f"{ticker} · {sector}", C_PURPLE)

    # Score + Classification header
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:16px;"
        f"background:{BG_CARD2};border:1px solid {BORDER};"
        f"border-left:3px solid {cls_color};border-radius:10px;"
        f"padding:1rem 1.4rem;margin-bottom:0.75rem;'>"
        f"<div style='display:flex;flex-direction:column;align-items:center;"
        f"min-width:80px;'>"
        f"<div style='font-size:2rem;font-weight:900;color:{cls_color};"
        f"font-family:\"JetBrains Mono\",monospace;line-height:1;'>{score:.0f}</div>"
        f"<div style='font-size:0.58rem;color:{TEXT_MUTED};text-transform:uppercase;"
        f"letter-spacing:0.1em;font-family:Inter,sans-serif;'>Score QV</div>"
        f"</div>"
        f"<div style='flex:1;'>"
        f"<div style='font-size:1.05rem;font-weight:800;color:{cls_color};"
        f"font-family:Inter,sans-serif;'>◈ {classification}</div>"
        f"<div style='font-size:0.75rem;color:{TEXT_SECONDARY};margin-top:2px;"
        f"font-family:Inter,sans-serif;'>{ticker} — {sector}</div>"
        f"<div style='margin-top:8px;height:5px;border-radius:3px;"
        f"background:rgba(255,255,255,0.06);overflow:hidden;'>"
        f"<div style='width:{score:.0f}%;height:100%;border-radius:3px;"
        f"background:linear-gradient(90deg,{cls_color},{cls_color}66);'></div>"
        f"</div>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)

    with c1:
        pl_color = C_POS if data["pl"] < data.get("pl_setor", 12) else (C_WARN if data["pl"] < data.get("pl_setor", 12) * 1.3 else C_NEG)
        pvp_color = C_POS if data["pvp"] < 1.5 else (C_WARN if data["pvp"] < 3 else C_NEG)
        roe_color = C_POS if data["roe"] > 15 else (C_WARN if data["roe"] > 8 else C_NEG)

        st.markdown(
            f"<div style='background:{BG_CARD};border:1px solid {BORDER};"
            f"border-radius:10px;padding:1rem 1.2rem;'>"
            f"<div style='font-size:0.68rem;font-weight:700;text-transform:uppercase;"
            f"letter-spacing:0.08em;color:{TEXT_MUTED};margin-bottom:0.5rem;"
            f"font-family:Inter,sans-serif;'>▪ Múltiplos de Mercado</div>"
            + _metric_row("P/L", f"{data['pl']:.1f}x", f"Setor: {data.get('pl_setor',12):.1f}x", pl_color)
            + _metric_row("P/VP", f"{data['pvp']:.1f}x", "Book Value", pvp_color)
            + _metric_row("EV/EBITDA", f"{data['ev_ebitda']:.1f}x", "", C_NEUT2)
            + f"</div>",
            unsafe_allow_html=True,
        )

    with c2:
        dy_color = C_POS if data["dy"] > 5 else (C_WARN if data["dy"] > 2 else TEXT_SECONDARY)
        dl_color = C_POS if data["div_liq_ebitda"] < 2 else (C_WARN if data["div_liq_ebitda"] < 3.5 else C_NEG)

        st.markdown(
            f"<div style='background:{BG_CARD};border:1px solid {BORDER};"
            f"border-radius:10px;padding:1rem 1.2rem;'>"
            f"<div style='font-size:0.68rem;font-weight:700;text-transform:uppercase;"
            f"letter-spacing:0.08em;color:{TEXT_MUTED};margin-bottom:0.5rem;"
            f"font-family:Inter,sans-serif;'>▪ Retorno & Endividamento</div>"
            + _metric_row("ROE", f"{data['roe']:.1f}%", "Return on Equity", roe_color)
            + _metric_row("ROIC", f"{data['roic']:.1f}%", "Return on Invested Capital", C_NEUT2)
            + _metric_row("DY", f"{data['dy']:.1f}%", f"Payout: {data['payout']:.0f}%", dy_color)
            + _metric_row("Dív.Liq/EBITDA", f"{data['div_liq_ebitda']:.1f}x", "", dl_color)
            + f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)

    # Radar chart
    categories = ["P/L vs Setor", "ROE", "ROIC", "DY", "Solvência", "P/VP"]

    pl_score = max(0, min(100, (data.get("pl_setor", 12) / data["pl"]) * 50))
    roe_s    = min(100, data["roe"] * 3)
    roic_s   = min(100, data["roic"] * 3.5)
    dy_s     = min(100, data["dy"] * 8)
    solv_s   = max(0, min(100, (4 - data["div_liq_ebitda"]) * 25))
    pvp_s    = max(0, min(100, (3 / data["pvp"]) * 50))

    vals = [pl_score, roe_s, roic_s, dy_s, solv_s, pvp_s]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=vals + [vals[0]],
        theta=categories + [categories[0]],
        fill="toself",
        fillcolor=f"rgba(139,92,246,0.12)",
        line=dict(color=C_PURPLE, width=2),
        name=ticker,
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, 100],
                            gridcolor="rgba(255,255,255,0.06)",
                            tickfont=dict(color=TEXT_MUTED, size=8),
                            tickvals=[25, 50, 75, 100]),
            angularaxis=dict(gridcolor="rgba(255,255,255,0.06)",
                             linecolor=BORDER_LIGHT,
                             tickfont=dict(color=TEXT_SECONDARY, size=11)),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        height=280,
        margin=dict(t=20, b=20, l=50, r=50),
        font=dict(family="Inter, sans-serif", color=TEXT_SECONDARY),
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True)

    insight_str = (
        f"Score de valuation {score:.0f}/100 — classificado como <b>{classification}</b>. "
        f"P/L de {data['pl']:.1f}x vs setor em {data.get('pl_setor',12):.1f}x | "
        f"ROE {data['roe']:.1f}% | DY {data['dy']:.1f}%."
    )
    insight_box(insight_str, cls_color)
