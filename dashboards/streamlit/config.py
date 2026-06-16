"""Finance Dashboard — Configuration & Constants."""
from __future__ import annotations

import os

API_URL = os.getenv("API_URL", "http://localhost:8000/api/v1")

# ── Color Palette — Premium Dark Theme ──────────────────────────────────────
COLORS = {
    "bg_primary": "#080d1a",
    "bg_secondary": "#0d1424",
    "bg_card": "#111827",
    "bg_card_hover": "#162033",
    "bg_sidebar": "#090e1c",
    "border": "rgba(255,255,255,0.05)",
    "border_light": "rgba(255,255,255,0.08)",
    "border_accent": "rgba(59,130,246,0.35)",
    "accent": "#2563eb",
    "accent_light": "#3b82f6",
    "accent_glow": "rgba(59,130,246,0.12)",
    "success": "#10b981",
    "success_bright": "#00d4aa",
    "success_glow": "rgba(16,185,129,0.12)",
    "danger": "#ef4444",
    "danger_glow": "rgba(239,68,68,0.12)",
    "warning": "#f59e0b",
    "warning_glow": "rgba(245,158,11,0.12)",
    "text_primary": "#f1f5f9",
    "text_secondary": "#94a3b8",
    "text_muted": "#475569",
    "chart_bg": "rgba(0,0,0,0)",
    "grid": "rgba(255,255,255,0.035)",
}

# ── Plotly Base Layout ────────────────────────────────────────────────────────
CHART_LAYOUT: dict = {
    "template": "plotly_dark",
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "font": {"family": "Inter, system-ui, sans-serif", "color": "#94a3b8", "size": 12},
    "title": {"text": "", "font": {"family": "Inter, system-ui, sans-serif", "color": "#f1f5f9", "size": 15}},
    "xaxis": {
        "title": {"text": ""},
        "gridcolor": "rgba(255,255,255,0.035)",
        "linecolor": "rgba(255,255,255,0.06)",
        "tickcolor": "rgba(255,255,255,0)",
        "tickfont": {"color": "#64748b", "size": 11},
        "zerolinecolor": "rgba(255,255,255,0.06)",
        "showspikes": True,
        "spikecolor": "rgba(59,130,246,0.4)",
        "spikethickness": 1,
        "spikedash": "dot",
    },
    "yaxis": {
        "title": {"text": ""},
        "gridcolor": "rgba(255,255,255,0.035)",
        "linecolor": "rgba(255,255,255,0.06)",
        "tickcolor": "rgba(255,255,255,0)",
        "tickfont": {"color": "#64748b", "size": 11},
        "zerolinecolor": "rgba(255,255,255,0.06)",
        "showspikes": True,
        "spikecolor": "rgba(59,130,246,0.4)",
        "spikethickness": 1,
        "spikedash": "dot",
    },
    "margin": {"t": 48, "b": 32, "l": 52, "r": 16},
    "legend": {
        "bgcolor": "rgba(13,20,36,0.8)",
        "bordercolor": "rgba(255,255,255,0.06)",
        "borderwidth": 1,
        "font": {"color": "#94a3b8", "size": 11},
    },
    "hoverlabel": {
        "bgcolor": "#162033",
        "bordercolor": "#2563eb",
        "font": {"color": "#f1f5f9", "family": "Inter, system-ui, sans-serif", "size": 12},
        "align": "left",
    },
    "colorway": [
        "#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6",
        "#06b6d4", "#f97316", "#ec4899", "#84cc16", "#14b8a6",
    ],
}

# ── Color Sequences ───────────────────────────────────────────────────────────
PALETTE = [
    "#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6",
    "#06b6d4", "#f97316", "#ec4899", "#84cc16", "#14b8a6",
]

# ── B3 Ticker Universe ────────────────────────────────────────────────────────
TICKER_UNIVERSE: dict[str, str] = {
    "PETR4": "Petrobras · Petróleo e Gás",
    "VALE3": "Vale · Mineração",
    "ITUB4": "Itaú Unibanco · Bancos",
    "BBDC4": "Bradesco · Bancos",
    "BBAS3": "Banco do Brasil · Bancos",
    "SANB11": "Santander Brasil · Bancos",
    "WEGE3": "WEG · Bens Industriais",
    "EMBR3": "Embraer · Bens Industriais",
    "ABEV3": "Ambev · Bebidas",
    "JBSS3": "JBS · Alimentos",
    "BBSE3": "BB Seguridade · Seguros",
    "TAEE11": "Taesa · Energia Elétrica",
    "EGIE3": "Engie Brasil · Energia Elétrica",
    "ELET3": "Eletrobras · Energia Elétrica",
    "CMIG4": "CEMIG · Energia Elétrica",
    "PRIO3": "PetroRio · Petróleo e Gás",
    "CSAN3": "Cosan · Petróleo e Gás",
    "SUZB3": "Suzano · Papel e Celulose",
    "KLBN11": "Klabin · Papel e Celulose",
    "MGLU3": "Magazine Luiza · Varejo",
    "LREN3": "Lojas Renner · Varejo",
    "ASAI3": "Assaí Atacadista · Varejo Alimentar",
    "TOTS3": "Totvs · Tecnologia",
    "CYRE3": "Cyrela · Construção Civil",
    "RAIL3": "Rumo · Logística",
    "RENT3": "Localiza · Locação de Veículos",
    "SBSP3": "Sabesp · Saneamento",
    "RADL3": "RaiaDrogasil · Saúde",
    "HAPV3": "Hapvida · Saúde",
    "VIVT3": "Telefônica Brasil · Telecomunicações",
    "CPFE3": "CPFL Energia · Energia Elétrica",
    "EQTL3": "Equatorial Energia · Energia Elétrica",
    "BRFS3": "BRF · Alimentos",
    "TIMS3": "TIM · Telecomunicações",
}

SECTOR_COLORS: dict[str, str] = {
    "Petróleo e Gás": "#f59e0b",
    "Mineração": "#8b5cf6",
    "Bancos": "#3b82f6",
    "Bens Industriais": "#06b6d4",
    "Bebidas": "#ef4444",
    "Alimentos": "#f97316",
    "Seguros": "#14b8a6",
    "Energia Elétrica": "#10b981",
    "Papel e Celulose": "#84cc16",
    "Varejo": "#ec4899",
    "Varejo Alimentar": "#a855f7",
    "Tecnologia": "#22d3ee",
    "Construção Civil": "#fb923c",
    "Logística": "#94a3b8",
    "Locação de Veículos": "#fbbf24",
    "Saneamento": "#60a5fa",
    "Saúde": "#34d399",
    "Telecomunicações": "#c084fc",
}

# ── Derived maps — single source of truth, derived from TICKER_UNIVERSE ──────
# Format of each value: "Name · Sector"  →  split on "·" to get sector.
SECTORS: dict[str, str] = {
    ticker: label.split("·")[1].strip()
    for ticker, label in TICKER_UNIVERSE.items()
}

# Subset used for performance rankings (most liquid names).
# Kept explicit so maintainers can tune it without touching TICKER_UNIVERSE.
RANK_TICKERS: list[str] = [
    "PETR4", "VALE3", "ITUB4", "BBDC4", "BBAS3", "WEGE3", "ABEV3",
    "RENT3", "EMBR3", "RAIL3", "TOTS3", "RADL3", "BBSE3", "EGIE3",
    "TAEE11", "ELET3", "CMIG4", "SUZB3", "PRIO3", "SANB11",
    "ASAI3", "LREN3", "JBSS3", "VIVT3", "SBSP3",
]

# ── Navigation Pages ──────────────────────────────────────────────────────────
PAGES = [
    ("Market Overview", "overview"),
    ("Stock Analysis", "analysis"),
    ("Investment Insights", "insights"),
    ("Market Heatmap", "heatmap"),
    ("Forecasting", "forecast"),
    ("Macro Indicators", "macro"),
    ("Rankings", "rankings"),
    ("Compare Assets", "compare"),
]
