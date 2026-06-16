"""Finance — Stock Analysis Page (TradingView-style)."""
from __future__ import annotations

import math
import pandas as pd
import streamlit as st

from utils.api import fetch, to_float
from utils.charts import candlestick_with_indicators
from utils.ui import section_header, apply_period_filter


def render(ticker: str) -> None:
    section_header("Análise de Ações", "#3b82f6")
    st.markdown(
        f"<div style='margin-top:-0.5rem;margin-bottom:0.8rem;'>"
        f"<span style='font-size:1.1rem;font-weight:700;color:#3b82f6;"
        f"font-family:\"JetBrains Mono\",monospace;'>{ticker}</span></div>",
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
    with c1:
        period = st.selectbox("Período", ["1y", "6mo", "3mo", "1mo", "5d"], key="sa_period")
    with c2:
        ma_opts = st.multiselect("Médias Móveis", [20, 50, 200], default=[20, 50], key="sa_ma")
    with c3:
        show_rsi = st.checkbox("RSI(14)", value=True, key="sa_rsi")
    with c4:
        show_macd = st.checkbox("MACD", value=False, key="sa_macd")

    with st.spinner(f"Carregando {ticker}..."):
        data = fetch(f"/stocks/{ticker}/history", {"period": period})

    if not data or not data.get("cotacoes"):
        st.info(f"Sem dados para **{ticker}**. Verifique a conectividade com a API.")
        return

    df = pd.DataFrame(data["cotacoes"])
    df["data"] = pd.to_datetime(df["data"])
    for col in ["fechamento", "abertura", "maxima", "minima"]:
        df[col] = df[col].apply(to_float)
    if "volume" in df.columns:
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0)
    df = df.dropna(subset=["fechamento", "abertura", "maxima", "minima"])
    df = apply_period_filter(df)

    last_close = df["fechamento"].iloc[-1]
    prev_close = df["fechamento"].iloc[-2] if len(df) > 1 else last_close
    chg_pct = (last_close - prev_close) / prev_close * 100 if prev_close else 0
    high_52w = df["maxima"].max()
    low_52w = df["minima"].min()
    avg_vol = df["volume"].mean() if "volume" in df.columns else 0
    total_ret = (last_close / df["fechamento"].iloc[0] - 1) * 100 if df["fechamento"].iloc[0] else 0

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.metric("Preço", f"R$ {last_close:.2f}", f"{chg_pct:+.2f}%")
    with k2:
        st.metric(f"Retorno {period}", f"{total_ret:+.1f}%")
    with k3:
        st.metric("Máxima 52s", f"R$ {high_52w:.2f}")
    with k4:
        st.metric("Mínima 52s", f"R$ {low_52w:.2f}")
    with k5:
        st.metric("Vol. Médio", f"{avg_vol/1e6:.1f}M" if avg_vol > 0 else "—")

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # Compute indicator series once — shared by chart and indicators table below
    close = df["fechamento"]
    _ma20_s  = close.rolling(20).mean()  if len(df) >= 20  else None
    _ma50_s  = close.rolling(50).mean()  if len(df) >= 50  else None
    _ma200_s = close.rolling(200).mean() if len(df) >= 200 else None
    _std20_s = close.rolling(20).std()   if len(df) >= 20  else None

    _delta = close.diff()
    _gain  = _delta.clip(lower=0).rolling(14).mean()
    _loss  = (-_delta.clip(upper=0)).rolling(14).mean()
    _rs    = _gain / _loss.replace(0, float("nan"))
    _rsi_s = (100 - 100 / (1 + _rs)) if len(df) >= 15 else None

    _precomputed: dict[str, pd.Series] = {}
    if _ma20_s  is not None: _precomputed["ma20"]  = _ma20_s
    if _ma50_s  is not None: _precomputed["ma50"]  = _ma50_s
    if _ma200_s is not None: _precomputed["ma200"] = _ma200_s
    if _std20_s is not None: _precomputed["std20"] = _std20_s
    if _rsi_s   is not None: _precomputed["rsi"]   = _rsi_s

    fig = candlestick_with_indicators(
        df=df,
        ticker=ticker,
        show_volume=True,
        show_rsi=show_rsi,
        show_macd=show_macd,
        ma_periods=ma_opts or [20, 50],
        precomputed=_precomputed,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("<div style='height:2rem'></div>", unsafe_allow_html=True)
    section_header("Indicadores Técnicos", "#a855f7")

    # Scalars for the table — derived from the already-computed series
    ma20  = float(_ma20_s.iloc[-1])  if _ma20_s  is not None else None
    ma50  = float(_ma50_s.iloc[-1])  if _ma50_s  is not None else None
    ma200 = float(_ma200_s.iloc[-1]) if _ma200_s is not None else None

    _rsi_raw = _rsi_s.iloc[-1] if _rsi_s is not None else None
    rsi_val = None if (_rsi_raw is None or (isinstance(_rsi_raw, float) and math.isnan(_rsi_raw))) else float(_rsi_raw)

    bb_upper = float((_ma20_s + 2 * _std20_s).iloc[-1]) if _ma20_s is not None and _std20_s is not None else None
    bb_lower = float((_ma20_s - 2 * _std20_s).iloc[-1]) if _ma20_s is not None and _std20_s is not None else None

    def _signal(price: float, ma: float | None) -> str:
        if ma is None:
            return "—"
        return "▲ Acima" if price > ma else "▼ Abaixo"

    def _signal_color(price: float, ma: float | None) -> str:
        if ma is None:
            return "#475569"
        return "#10b981" if price > ma else "#ef4444"

    def _rsi_display(r: float | None) -> tuple[str, str]:
        if r is None:
            return "—", "#475569"
        if r >= 70:
            return f"{r:.1f} Sobrecomprado", "#ef4444"
        if r <= 30:
            return f"{r:.1f} Sobrevendido", "#10b981"
        return f"{r:.1f} Neutro", "#94a3b8"

    rsi_text, rsi_color = _rsi_display(rsi_val)

    indicators = [
        ("MA(20)", f"R$ {ma20:.2f}" if ma20 else "—", _signal(last_close, ma20), _signal_color(last_close, ma20)),
        ("MA(50)", f"R$ {ma50:.2f}" if ma50 else "—", _signal(last_close, ma50), _signal_color(last_close, ma50)),
        ("MA(200)", f"R$ {ma200:.2f}" if ma200 else "—", _signal(last_close, ma200), _signal_color(last_close, ma200)),
        ("RSI(14)", f"{rsi_val:.1f}" if rsi_val else "—", rsi_text, rsi_color),
        ("BB Upper(20)", f"R$ {bb_upper:.2f}" if bb_upper else "—", "", "#475569"),
        ("BB Lower(20)", f"R$ {bb_lower:.2f}" if bb_lower else "—", "", "#475569"),
    ]

    from utils.ui import render_dark_table
    df_tech = pd.DataFrame(indicators, columns=["Indicador", "Valor", "Sinal", "_color"])
    cell_colors_sa: dict[tuple[int, str], str] = {
        (i, "Sinal"): row["_color"]
        for i, row in df_tech.iterrows()
        if row["_color"]
    }
    df_tech = df_tech.drop(columns=["_color"])
    render_dark_table(df_tech, cell_colors=cell_colors_sa)
