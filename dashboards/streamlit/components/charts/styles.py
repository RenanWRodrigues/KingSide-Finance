"""Finance Charts — Centralized Visual Design System."""
from __future__ import annotations

# ── Color Palette ─────────────────────────────────────────────────────────────
BG_PRIMARY   = "#07111F"
BG_SECONDARY = "#0B1426"
BG_CARD      = "#111827"
BG_CARD2     = "#172033"
BG_HOVER     = "#162033"

BORDER       = "rgba(255,255,255,0.05)"
BORDER_LIGHT = "rgba(255,255,255,0.08)"
GRID         = "rgba(255,255,255,0.035)"

TEXT_PRIMARY   = "#E5E7EB"
TEXT_SECONDARY = "#9CA3AF"
TEXT_MUTED     = "#475569"
TEXT_MONO      = "'JetBrains Mono', 'Fira Code', monospace"

C_POS    = "#10B981"
C_POS2   = "#34D399"
C_NEG    = "#EF4444"
C_NEG2   = "#F87171"
C_NEUT   = "#3B82F6"
C_NEUT2  = "#60A5FA"
C_WARN   = "#F59E0B"
C_PURPLE = "#8B5CF6"
C_CYAN   = "#06B6D4"

PALETTE = [C_NEUT, C_POS, C_WARN, C_NEG, C_PURPLE, C_CYAN, "#F97316", "#EC4899", "#84CC16", "#14B8A6"]

# ── Padrão TradingView: legenda vertical à direita, fora do plot ──────────────
LEGEND_RIGHT: dict = dict(
    orientation="v",
    yanchor="top",
    y=1,
    xanchor="left",
    x=1.02,
    bgcolor="rgba(0,0,0,0)",
    bordercolor="rgba(255,255,255,0.1)",
    borderwidth=1,
    font=dict(color="white", size=12),
)

# ── Base Plotly Layout ────────────────────────────────────────────────────────
def base_layout(**overrides) -> dict:
    layout = {
        "template": "plotly_dark",
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"family": "Inter, system-ui, sans-serif", "color": TEXT_SECONDARY, "size": 12},
        "title": {"text": "", "font": {"family": "Inter, system-ui, sans-serif", "color": TEXT_PRIMARY, "size": 14}},
        "xaxis": {
            "title": {"text": ""},
            "gridcolor": GRID,
            "linecolor": BORDER_LIGHT,
            "tickcolor": "rgba(0,0,0,0)",
            "tickfont": {"color": TEXT_MUTED, "size": 10},
            "zerolinecolor": BORDER_LIGHT,
            "showspikes": True,
            "spikecolor": "rgba(59,130,246,0.5)",
            "spikethickness": 1,
            "spikedash": "dot",
        },
        "yaxis": {
            "title": {"text": ""},
            "gridcolor": GRID,
            "linecolor": BORDER_LIGHT,
            "tickcolor": "rgba(0,0,0,0)",
            "tickfont": {"color": TEXT_MUTED, "size": 10},
            "zerolinecolor": BORDER_LIGHT,
            "showspikes": True,
            "spikecolor": "rgba(59,130,246,0.5)",
            "spikethickness": 1,
            "spikedash": "dot",
        },
        "margin": {"t": 52, "b": 36, "l": 56, "r": 150},
        "legend": {
            "orientation": "v",
            "yanchor": "top",
            "y": 1,
            "xanchor": "left",
            "x": 1.02,
            "bgcolor": "rgba(0,0,0,0)",
            "bordercolor": "rgba(255,255,255,0.1)",
            "borderwidth": 1,
            "font": {"color": "white", "size": 12},
        },
        "hoverlabel": {
            "bgcolor": "#162033",
            "bordercolor": C_NEUT,
            "font": {"color": TEXT_PRIMARY, "family": "Inter, system-ui, sans-serif", "size": 12},
            "align": "left",
        },
        "colorway": PALETTE,
        "hovermode": "x unified",
        "modebar": {
            "bgcolor": "rgba(11,20,38,0.8)",
            "color": TEXT_MUTED,
            "activecolor": C_NEUT2,
        },
    }
    for key, val in overrides.items():
        if isinstance(val, dict) and key in layout and isinstance(layout[key], dict):
            merged = dict(layout[key])
            merged.update(val)
            layout[key] = merged
        elif isinstance(val, dict) and (key.startswith("xaxis") or key.startswith("yaxis")):
            if "title" not in val:
                val = dict(val, title={"text": ""})
            layout[key] = val
        else:
            layout[key] = val
    return layout


def axis_style(
    *,
    show_grid: bool = True,
    title: str = "",
    suffix: str = "",
    prefix: str = "",
    tick_format: str = "",
) -> dict:
    return {
        "gridcolor": GRID if show_grid else "rgba(0,0,0,0)",
        "linecolor": BORDER_LIGHT,
        "tickcolor": "rgba(0,0,0,0)",
        "tickfont": {"color": TEXT_MUTED, "size": 10},
        "title_text": title,
        "title_font": {"color": TEXT_SECONDARY, "size": 11},
        "ticksuffix": suffix,
        "tickprefix": prefix,
        "tickformat": tick_format,
        "zerolinecolor": BORDER_LIGHT,
        "showspikes": True,
        "spikecolor": "rgba(59,130,246,0.4)",
        "spikethickness": 1,
        "spikedash": "dot",
    }
