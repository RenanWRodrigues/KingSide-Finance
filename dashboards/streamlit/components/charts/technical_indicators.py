"""Finance Charts — Painel de Indicadores Técnicos (TradingView style)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from .styles import (
    C_NEG, C_NEUT, C_NEUT2, C_POS, C_WARN, C_PURPLE, C_CYAN,
    TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY, LEGEND_RIGHT, base_layout,
)
from .utils import (
    insight_box, kpi_card, section_header_charts, _seed, _generate_price_history,
)


def _calc_rsi(closes: pd.Series, period: int = 14) -> pd.Series:
    delta = closes.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def _calc_macd(closes: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    ema12  = closes.ewm(span=12, adjust=False).mean()
    ema26  = closes.ewm(span=26, adjust=False).mean()
    macd   = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    hist   = macd - signal
    return macd, signal, hist


def _calc_bbands(closes: pd.Series, period: int = 20, std: float = 2.0) -> tuple[pd.Series, pd.Series, pd.Series]:
    ma    = closes.rolling(period).mean()
    sigma = closes.rolling(period).std()
    return ma + std * sigma, ma, ma - std * sigma


def _calc_vwap(df: pd.DataFrame) -> pd.Series:
    if "volume" not in df.columns:
        return df["fechamento"].copy()
    typical = (df.get("maxima", df["fechamento"]) +
               df.get("minima",  df["fechamento"]) +
               df["fechamento"]) / 3
    return (typical * df["volume"]).cumsum() / df["volume"].cumsum()


def _signal_label(price: float, ma: float | None) -> tuple[str, str]:
    if ma is None:
        return "—", TEXT_MUTED
    return ("▲ Acima", C_POS) if price >= ma else ("▼ Abaixo", C_NEG)


def _rsi_label(rsi: float | None) -> tuple[str, str]:
    if rsi is None:
        return "—", TEXT_MUTED
    if rsi >= 70:
        return f"{rsi:.1f} · Sobrecomprado", C_NEG
    if rsi <= 30:
        return f"{rsi:.1f} · Sobrevendido", C_POS
    return f"{rsi:.1f} · Neutro", C_NEUT2


def _auto_insight(df: pd.DataFrame) -> str:
    closes = df["fechamento"]
    rsi_raw = _calc_rsi(closes).iloc[-1]
    rsi = None if pd.isna(rsi_raw) else float(rsi_raw)
    ma20 = closes.rolling(20).mean().iloc[-1] if len(df) >= 20 else None
    ma50 = closes.rolling(50).mean().iloc[-1] if len(df) >= 50 else None
    if ma20 is not None and pd.isna(ma20):
        ma20 = None
    if ma50 is not None and pd.isna(ma50):
        ma50 = None
    price = closes.iloc[-1]
    signals = []
    if ma20 is not None and price > ma20:
        signals.append("acima da MM20")
    if ma50 is not None and price > ma50:
        signals.append("acima da MM50")

    rsi_interp = "em zona neutra"
    rsi_str = f"{rsi:.1f}" if rsi is not None else "—"
    if rsi is not None:
        if rsi >= 70:
            rsi_interp = "em zona de sobrecompra"
        elif rsi <= 30:
            rsi_interp = "em zona de sobrevenda"

    if signals:
        return (
            f"Preço {', '.join(signals)} com RSI {rsi_interp} ({rsi_str}). "
            "Estrutura técnica de curto prazo favorável — confirmar com volume e momentum."
        )
    return (
        f"Preço abaixo das médias móveis chave com RSI {rsi_interp} ({rsi_str}). "
        "Aguardar sinais de reversão ou confirmação antes de novas posições."
    )


def render_technical_indicators(
    df: pd.DataFrame | None = None,
    ticker: str = "TICKER",
    show_volume: bool = True,
) -> None:
    if df is None or df.empty:
        import random
        df = _generate_price_history(ticker)
        df["volume"] = [random.Random(_seed(ticker) + i).uniform(1e6, 8e6) for i in range(len(df))]
        df["abertura"] = df["fechamento"].shift(1).fillna(df["fechamento"])
        df["maxima"]   = df["fechamento"] * 1.01
        df["minima"]   = df["fechamento"] * 0.99

    closes = df["fechamento"]
    rsi    = _calc_rsi(closes)
    macd, signal_line, macd_hist = _calc_macd(closes)
    bb_upper, bb_mid, bb_lower = _calc_bbands(closes)
    vwap = _calc_vwap(df)

    ma20  = closes.rolling(20).mean()
    ma50  = closes.rolling(50).mean()
    ma200 = closes.rolling(200).mean()
    ema9  = closes.ewm(span=9).mean()

    price_now = closes.iloc[-1]
    rsi_now   = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else None
    ma20_now  = ma20.iloc[-1] if len(df) >= 20 else None
    ma50_now  = ma50.iloc[-1] if len(df) >= 50 else None
    ma200_now = ma200.iloc[-1] if len(df) >= 200 else None

    section_header_charts(
        "Indicadores Técnicos Avançados",
        f"{ticker} · RSI | MACD | Bollinger | EMA | SMA | VWAP",
        C_NEUT,
    )

    # Signal summary cards
    rsi_lbl, rsi_col   = _rsi_label(rsi_now)
    sig20, col20 = _signal_label(price_now, ma20_now)
    sig50, col50 = _signal_label(price_now, ma50_now)
    sig200, col200 = _signal_label(price_now, ma200_now)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(kpi_card("Preço", f"R$ {price_now:.2f}", accent=C_NEUT, icon="◉"), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card("RSI(14)", rsi_lbl, accent=rsi_col if rsi_now else TEXT_MUTED, icon="◎"), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi_card("vs MM20", sig20, f"R$ {ma20_now:.2f}" if ma20_now else "—",
                             price_now >= (ma20_now or 0), col20, "≈"), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi_card("vs MM50", sig50, f"R$ {ma50_now:.2f}" if ma50_now else "—",
                             price_now >= (ma50_now or 0), col50, "≈"), unsafe_allow_html=True)
    with c5:
        st.markdown(kpi_card("vs MM200", sig200, f"R$ {ma200_now:.2f}" if ma200_now else "—",
                             price_now >= (ma200_now or 0), col200, "≈"), unsafe_allow_html=True)

    st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)

    n_rows = 3 + (1 if show_volume else 0)
    row_heights = [0.50, 0.22, 0.28] if not show_volume else [0.44, 0.10, 0.22, 0.24]
    fig = make_subplots(
        rows=n_rows, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.09,
        row_heights=row_heights,
        subplot_titles=([f"{ticker} — Preço + Indicadores", "Volume", "RSI(14)", "MACD"]
                        if show_volume else [f"{ticker} — Preço + Indicadores", "RSI(14)", "MACD"]),
    )

    price_row = 1
    vol_row   = 2 if show_volume else None
    rsi_row   = 3 if show_volume else 2
    macd_row  = 4 if show_volume else 3

    # Candlestick
    if "abertura" in df.columns:
        fig.add_trace(go.Candlestick(
            x=df["data"],
            open=df["abertura"], high=df["maxima"],
            low=df["minima"],   close=closes,
            name=ticker,
            increasing=dict(fillcolor=C_POS,  line=dict(color=C_POS,  width=1)),
            decreasing=dict(fillcolor=C_NEG,  line=dict(color=C_NEG,  width=1)),
            whiskerwidth=0.5,
        ), row=price_row, col=1)
    else:
        fig.add_trace(go.Scatter(
            x=df["data"], y=closes,
            name=ticker,
            mode="lines",
            line=dict(color=C_NEUT, width=1.8),
        ), row=price_row, col=1)

    # Bollinger Bands
    x_bb = pd.concat([df["data"], df["data"].iloc[::-1]])
    y_bb = pd.concat([bb_upper, bb_lower.iloc[::-1]])
    fig.add_trace(go.Scatter(
        x=x_bb, y=y_bb, fill="toself",
        fillcolor="rgba(59,130,246,0.06)",
        line=dict(color="rgba(0,0,0,0)"),
        name="BB(20,2)", showlegend=True,
    ), row=price_row, col=1)
    fig.add_trace(go.Scatter(x=df["data"], y=bb_upper, name="BB Upper",
                             line=dict(color="rgba(59,130,246,0.4)", width=0.8, dash="dot"),
                             showlegend=False), row=price_row, col=1)
    fig.add_trace(go.Scatter(x=df["data"], y=bb_lower, name="BB Lower",
                             line=dict(color="rgba(59,130,246,0.4)", width=0.8, dash="dot"),
                             showlegend=False), row=price_row, col=1)

    # MAs
    for ma, color, name in [
        (ma20,  "#3B82F6", "MM20"),
        (ma50,  "#F59E0B", "MM50"),
        (ma200, "#8B5CF6", "MM200"),
        (vwap,  "#06B6D4", "VWAP"),
    ]:
        if ma is not None and not ma.isna().all():
            fig.add_trace(go.Scatter(
                x=df["data"], y=ma, name=name,
                line=dict(color=color, width=1.4),
                opacity=0.85,
            ), row=price_row, col=1)

    # Volume
    if show_volume and "volume" in df.columns and vol_row:
        vol_colors = [C_POS if c >= o else C_NEG
                      for c, o in zip(df["fechamento"], df.get("abertura", df["fechamento"]))]
        fig.add_trace(go.Bar(
            x=df["data"], y=df["volume"],
            name="Volume",
            marker=dict(color=vol_colors, opacity=0.65),
            showlegend=False,
        ), row=vol_row, col=1)

    # RSI
    fig.add_trace(go.Scatter(
        x=df["data"], y=rsi,
        name="RSI(14)",
        line=dict(color=C_PURPLE, width=1.8),
        fill="tozeroy", fillcolor="rgba(139,92,246,0.07)",
    ), row=rsi_row, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="rgba(239,68,68,0.33)", row=rsi_row, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="rgba(16,185,129,0.33)", row=rsi_row, col=1)
    fig.add_hrect(y0=30, y1=70, fillcolor="rgba(139,92,246,0.02)", line_width=0, row=rsi_row, col=1)
    fig.update_yaxes(range=[0, 100], row=rsi_row, col=1)

    # MACD
    hist_colors = [C_POS if v >= 0 else C_NEG for v in macd_hist]
    fig.add_trace(go.Bar(
        x=df["data"], y=macd_hist,
        name="MACD Hist",
        marker=dict(color=hist_colors, opacity=0.7),
        showlegend=False,
    ), row=macd_row, col=1)
    fig.add_trace(go.Scatter(
        x=df["data"], y=macd, name="MACD",
        line=dict(color=C_NEUT, width=1.5),
    ), row=macd_row, col=1)
    fig.add_trace(go.Scatter(
        x=df["data"], y=signal_line, name="Signal",
        line=dict(color=C_WARN, width=1.5, dash="dash"),
    ), row=macd_row, col=1)
    fig.add_hline(y=0, line_dash="dot", line_color="rgba(255,255,255,0.12)", row=macd_row, col=1)

    total_height = 580 if not show_volume else 720
    fig.update_layout(**base_layout(
        height=total_height,
        hovermode="x unified",
        xaxis_rangeslider_visible=False,
        margin=dict(b=64, r=150),
        legend=LEGEND_RIGHT,
    ))

    for r in range(1, n_rows + 1):
        fig.update_xaxes(title_text="", gridcolor="rgba(255,255,255,0.025)",
                         tickfont=dict(color=TEXT_MUTED, size=9), row=r, col=1)
        fig.update_yaxes(title_text="", gridcolor="rgba(255,255,255,0.025)",
                         tickfont=dict(color=TEXT_MUTED, size=9), row=r, col=1)

    st.plotly_chart(fig, use_container_width=True, config={
        "displayModeBar": True,
        "modeBarButtonsToRemove": ["lasso2d", "select2d"],
        "toImageButtonOptions": {"format": "png", "scale": 2},
    })

    insight_box(_auto_insight(df), C_NEUT)
