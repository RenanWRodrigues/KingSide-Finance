"""Finance — UI helper utilities for safe single-line HTML rendering."""
from __future__ import annotations

import pandas as pd
import streamlit as st

_MONTH_NAMES_PT = [
    "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


def any_period_filter_active() -> bool:
    """Return True if any of the sidebar time filters is not 'Todos'."""
    return any(
        st.session_state.get(k, "Todos") != "Todos"
        for k in ("filter_ano", "filter_mes", "filter_dia")
    )


def filter_cotacoes_by_period(cotacoes: list, min_rows: int = 30) -> list:
    """Filter a list of cotacao dicts by the sidebar time filters.

    Falls back to the original list when the result would be shorter than
    min_rows (prevents scoring algorithms from crashing with too little data).
    """
    ano = st.session_state.get("filter_ano", "Todos")
    mes = st.session_state.get("filter_mes", "Todos")
    dia = st.session_state.get("filter_dia", "Todos")

    if ano == "Todos" and mes == "Todos" and dia == "Todos":
        return cotacoes

    filtered = []
    for c in cotacoes:
        try:
            dt = pd.to_datetime(c.get("data"))
            if ano != "Todos" and dt.year != int(ano):
                continue
            if mes != "Todos":
                month_num = _MONTH_NAMES_PT.index(mes) if mes in _MONTH_NAMES_PT else 0
                if month_num and dt.month != month_num:
                    continue
            if dia != "Todos" and dt.day != int(dia):
                continue
            filtered.append(c)
        except Exception:
            filtered.append(c)

    return filtered if len(filtered) >= min_rows else cotacoes


def apply_period_filter(
    df: pd.DataFrame | None,
    date_col: str = "data",
    year_col: str | None = None,
) -> pd.DataFrame | None:
    """Filter a DataFrame by the sidebar Ano/Mês/Dia selectors.

    For annual DataFrames that only have an integer year column (e.g. 'ano'),
    pass year_col='ano' — only the Ano filter will be applied.
    Returns the original df unchanged when the filtered result would be empty.
    """
    if df is None or df.empty:
        return df

    ano = st.session_state.get("filter_ano", "Todos")
    mes = st.session_state.get("filter_mes", "Todos")
    dia = st.session_state.get("filter_dia", "Todos")

    if ano == "Todos" and mes == "Todos" and dia == "Todos":
        return df

    # Annual data: only the year filter is meaningful
    if year_col and year_col in df.columns:
        if ano == "Todos":
            return df
        filtered = df[df[year_col] == int(ano)]
        return filtered if not filtered.empty else df

    if date_col not in df.columns:
        return df

    dt = pd.to_datetime(df[date_col])
    mask = pd.Series(True, index=df.index)

    if ano != "Todos":
        mask &= dt.dt.year == int(ano)
    if mes != "Todos":
        month_num = _MONTH_NAMES_PT.index(mes) if mes in _MONTH_NAMES_PT else 0
        if month_num:
            mask &= dt.dt.month == month_num
    if dia != "Todos":
        mask &= dt.dt.day == int(dia)

    filtered = df[mask]
    return filtered if not filtered.empty else df

# ── Dark-theme pandas Styler helpers ─────────────────────────────────────────

_DARK_TABLE_STYLES: list[dict] = [
    {"selector": "table", "props": [
        ("background-color", "#111827"),
        ("border-collapse", "collapse"),
        ("width", "100%"),
    ]},
    {"selector": "thead tr th", "props": [
        ("background-color", "#0d1424"),
        ("color", "#475569"),
        ("font-size", "0.7rem"),
        ("font-weight", "600"),
        ("text-transform", "uppercase"),
        ("letter-spacing", "0.06em"),
        ("border-bottom", "1px solid rgba(255,255,255,0.07)"),
        ("padding", "0.65rem 0.9rem"),
        ("font-family", "'Inter', system-ui, sans-serif"),
        ("white-space", "nowrap"),
    ]},
    {"selector": "tbody td", "props": [
        ("background-color", "#111827"),
        ("color", "#94a3b8"),
        ("border-bottom", "1px solid rgba(255,255,255,0.04)"),
        ("padding", "0.55rem 0.9rem"),
        ("font-family", "'JetBrains Mono', 'Fira Code', monospace"),
        ("font-size", "0.82rem"),
    ]},
    {"selector": "tbody tr:hover td", "props": [
        ("background-color", "rgba(255,255,255,0.025)"),
    ]},
    {"selector": "tbody tr:nth-child(even) td", "props": [
        ("background-color", "rgba(13,20,36,0.55)"),
    ]},
]


def apply_dark_table_styles(styler: object) -> object:
    """Apply dark-theme CSS to a pandas Styler (kept for backward compatibility)."""
    return styler.set_table_styles(_DARK_TABLE_STYLES)  # type: ignore[union-attr]


# ── CSS constants for inline HTML tables ──────────────────────────────────────
_TBL_WRAP = (
    "overflow-x:auto;border-radius:10px;border:1px solid rgba(255,255,255,0.05);"
    "background:#111827;"
)
_TBL_TAG = (
    "width:100%;border-collapse:collapse;background:#111827;"
    "font-family:'Inter',system-ui,sans-serif;font-size:0.83rem;"
)
_TH_STYLE = (
    "background:#0d1424;color:#475569;font-size:0.69rem;font-weight:600;"
    "text-transform:uppercase;letter-spacing:0.07em;"
    "border-bottom:1px solid rgba(255,255,255,0.07);padding:0.65rem 0.9rem;"
    "white-space:nowrap;text-align:left;"
)
_TD_STYLE = (
    "background:#111827;color:#94a3b8;border-bottom:1px solid rgba(255,255,255,0.04);"
    "padding:0.55rem 0.9rem;font-family:'JetBrains Mono','Fira Code',monospace;"
    "font-size:0.82rem;"
)
_TD_EVEN = (
    "background:rgba(13,20,36,0.55);color:#94a3b8;"
    "border-bottom:1px solid rgba(255,255,255,0.04);"
    "padding:0.55rem 0.9rem;font-family:'JetBrains Mono','Fira Code',monospace;"
    "font-size:0.82rem;"
)


def render_dark_table(
    df: "pd.DataFrame",
    cell_colors: dict[tuple[int, str], str] | None = None,
    height: int | None = None,
    key: str = "",
) -> None:
    """Render a DataFrame as a dark-themed HTML table.

    Works correctly in Streamlit 1.40+ where st.dataframe uses canvas rendering
    that ignores pandas Styler CSS. All styles are inline — no theme dependency.

    Args:
        df: DataFrame to render.
        cell_colors: Optional {(row_idx, col_name): css_color} for cell text colors.
        height: Max height in px (adds vertical scroll). None = auto.
        key: Unused, kept for call-site compatibility.
    """
    import html as _html
    cell_colors = cell_colors or {}

    scroll_style = f"max-height:{height}px;overflow-y:auto;" if height else ""
    rows_html: list[str] = []

    # Header
    ths = "".join(f"<th style='{_TH_STYLE}'>{_html.escape(str(c))}</th>" for c in df.columns)
    rows_html.append(f"<thead><tr>{ths}</tr></thead>")

    # Body
    body_parts: list[str] = ["<tbody>"]
    for i, (_, row) in enumerate(df.iterrows()):
        td_base = _TD_EVEN if i % 2 else _TD_STYLE
        tds = []
        for col in df.columns:
            val = row[col]
            extra_color = cell_colors.get((i, col), "")
            color_style = f"color:{extra_color};" if extra_color else ""
            tds.append(
                f"<td style='{td_base}{color_style}'>{_html.escape(str(val) if val is not None else '—')}</td>"
            )
        body_parts.append(f"<tr>{''.join(tds)}</tr>")
    body_parts.append("</tbody>")
    rows_html.extend(body_parts)

    html = (
        f"<div style='{_TBL_WRAP}{scroll_style}'>"
        f"<table style='{_TBL_TAG}'>{''.join(rows_html)}</table>"
        f"</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def dark_gradient_cmap() -> object | None:
    """Return a dark-background-friendly gradient colormap: red → amber → green."""
    try:
        from matplotlib.colors import LinearSegmentedColormap
        return LinearSegmentedColormap.from_list(
            "DarkFinance", ["#ef4444", "#f59e0b", "#22c55e"]
        )
    except ImportError:
        return None


def section_header(title: str, color: str = "#3b82f6") -> None:
    """Render a section header with a colored dot."""
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:10px;"
        f"margin-bottom:0.8rem;padding-bottom:0.6rem;"
        f"border-bottom:1px solid rgba(255,255,255,0.05);'>"
        f"<div style='width:7px;height:7px;border-radius:50%;background:{color};"
        f"box-shadow:0 0 8px {color};flex-shrink:0;'></div>"
        f"<span style='font-size:0.82rem;font-weight:700;color:#f1f5f9;"
        f"text-transform:uppercase;letter-spacing:0.06em;"
        f"font-family:Inter,sans-serif;'>{title}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


def badge(signal: str) -> str:
    """Return single-line HTML badge for investment signal."""
    styles = {
        "Strong Buy":  ("rgba(0,212,170,0.18)", "#00d4aa", "rgba(0,212,170,0.35)", "◆ STRONG BUY"),
        "Buy":         ("rgba(16,185,129,0.15)", "#10b981", "rgba(16,185,129,0.3)", "▲ BUY"),
        "Neutral":     ("rgba(148,163,184,0.1)", "#94a3b8", "rgba(148,163,184,0.2)", "● NEUTRAL"),
        "Sell":        ("rgba(239,68,68,0.12)", "#ef4444", "rgba(239,68,68,0.25)", "▼ SELL"),
        "Strong Sell": ("rgba(239,68,68,0.2)", "#fca5a5", "rgba(239,68,68,0.4)", "◆ STRONG SELL"),
    }
    bg, color, border, label = styles.get(signal, styles["Neutral"])
    return (
        f"<span style='display:inline-flex;align-items:center;padding:2px 8px;"
        f"border-radius:20px;font-size:0.68rem;font-weight:700;letter-spacing:0.05em;"
        f"text-transform:uppercase;font-family:Inter,sans-serif;"
        f"background:{bg};color:{color};border:1px solid {border};'>{label}</span>"
    )


def score_bar_html(score: float) -> str:
    """Single-line HTML score progress bar."""
    color = "#10b981" if score >= 70 else ("#f59e0b" if score >= 50 else "#ef4444")
    return (
        f"<div style='display:flex;align-items:center;gap:8px;'>"
        f"<span style='font-size:1rem;font-weight:800;color:{color};"
        f"font-family:\"JetBrains Mono\",monospace;min-width:38px;'>{score:.1f}</span>"
        f"<div style='flex:1;height:4px;border-radius:2px;"
        f"background:rgba(255,255,255,0.08);overflow:hidden;'>"
        f"<div style='width:{score}%;height:100%;border-radius:2px;"
        f"background:linear-gradient(90deg,{color},{color}88);'></div></div></div>"
    )


def card_html(content: str, accent_color: str = "#2563eb") -> str:
    """Wrap content in a single-line card div."""
    return (
        f"<div style='background:#111827;border:1px solid rgba(255,255,255,0.05);"
        f"border-top:2px solid {accent_color};border-radius:10px;"
        f"padding:1rem;margin-bottom:0.5rem;'>{content}</div>"
    )


def stat_html(label: str, value: str, color: str = "#f1f5f9") -> str:
    """Single-line stat display."""
    return (
        f"<div style='margin-bottom:0.3rem;'>"
        f"<div style='font-size:0.62rem;font-weight:600;text-transform:uppercase;"
        f"letter-spacing:0.08em;color:#475569;font-family:Inter,sans-serif;'>{label}</div>"
        f"<div style='font-size:1rem;font-weight:700;color:{color};"
        f"font-family:\"JetBrains Mono\",monospace;'>{value}</div>"
        f"</div>"
    )
