"""Finance Charts — Correlação Macroeconômica com Dados Reais (SELIC, IPCA, Dólar)."""
from __future__ import annotations

import random

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .styles import (
    C_NEG, C_NEUT, C_NEUT2, C_POS, C_WARN, C_PURPLE, C_CYAN,
    TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY, PALETTE, LEGEND_RIGHT, base_layout,
)
from .utils import (
    insight_box, section_header_charts, _seed,
)

_MACRO_ENDPOINTS = [
    ("/macro/brasil/selic",       "SELIC (%)"),
    ("/macro/brasil/ipca",        "IPCA 12m (%)"),
    ("/macro/brasil/cambio_dolar", "USD/BRL"),
]


def _fetch_real_macro_df(ticker: str, price_df: pd.DataFrame | None) -> tuple[pd.DataFrame, bool]:
    """Build a monthly macro + stock return DataFrame from real API data.

    Returns (df, is_real). is_real=True when at least SELIC data was available.
    """
    from utils.api import fetch_parallel, to_float

    results = fetch_parallel(
        [(ep, None) for ep, _ in _MACRO_ENDPOINTS],
        timeout=12,
    )

    macro_series: dict[str, pd.Series] = {}
    any_real = False

    for (_, label), data in zip(_MACRO_ENDPOINTS, results):
        if not data or not isinstance(data, list):
            continue
        try:
            s = pd.Series(
                {pd.to_datetime(item["data"]): to_float(item["valor"]) for item in data}
            ).dropna()
            # Resample to month-start for alignment (avoids duplicate index from period conversion)
            s = s.resample("MS").last().dropna()
            macro_series[label] = s
            any_real = True
        except Exception:
            continue

    # Stock monthly returns from price_df
    stock_series: pd.Series | None = None
    if price_df is not None and not price_df.empty and "fechamento" in price_df.columns:
        try:
            pf = price_df.copy()
            pf["data"] = pd.to_datetime(pf["data"])
            pf = pf.set_index("data")["fechamento"].dropna()
            # Monthly returns
            monthly = pf.resample("ME").last().dropna()
            monthly.index = monthly.index.to_period("M").to_timestamp()
            stock_series = monthly.pct_change().dropna() * 100
            stock_series.name = f"{ticker} Retorno (%)"
        except Exception:
            stock_series = None

    if not any_real:
        return pd.DataFrame(), False

    # Align all series by month
    dfs = []
    for label, s in macro_series.items():
        dfs.append(s.rename(label))
    if stock_series is not None:
        dfs.append(stock_series)

    if not dfs:
        return pd.DataFrame(), False

    df = pd.concat(dfs, axis=1).dropna(how="all")
    # Keep last 36 months
    df = df.tail(36).reset_index().rename(columns={"index": "data"})
    return df, True


def _demo_macro_df(ticker: str, n: int = 36) -> pd.DataFrame:
    """Synthetic fallback — used only when the API returns no macro data."""
    rng    = random.Random(_seed(ticker) + 50)
    np_rng = np.random.RandomState(_seed(ticker) + 50)
    dates  = pd.date_range(end=pd.Timestamp.today(), periods=n, freq="ME")
    n      = len(dates)

    selic  = np.cumsum(np_rng.normal(0, 0.5, n)) + 11.5
    ipca   = np.cumsum(np_rng.normal(0, 0.15, n)) + 4.5
    dolar  = np.cumsum(np_rng.normal(0, 0.08, n)) + 5.0
    stock  = (
        -0.3 * (selic  - selic.mean())  / (selic.std()  or 1)
        + 0.2 * np_rng.normal(2.5, 0.6, n)
        - 0.15 * (ipca - ipca.mean()) / (ipca.std() or 1)
        + np_rng.normal(0, 0.3, n)
    ) * 3

    return pd.DataFrame({
        "data":               dates,
        "SELIC (%)":          np.clip(selic, 3, 20),
        "IPCA 12m (%)":       np.clip(ipca, 0, 15),
        "USD/BRL":            np.clip(dolar, 4.0, 8.0),
        f"{ticker} Retorno (%)": stock,
    })


def _correlation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    return df.select_dtypes(include=[float, int]).corr()


def _auto_insight(df: pd.DataFrame, ticker: str, is_real: bool) -> str:
    corr    = _correlation_matrix(df)
    ret_col = f"{ticker} Retorno (%)"
    if ret_col not in corr.columns:
        return "Análise de correlação não disponível."

    correlations  = corr[ret_col].drop(ret_col).sort_values(key=abs, ascending=False)
    strongest     = correlations.index[0]
    strongest_val = correlations.iloc[0]
    direction     = "positiva" if strongest_val > 0 else "negativa"
    strength      = "forte" if abs(strongest_val) > 0.5 else ("moderada" if abs(strongest_val) > 0.25 else "fraca")
    source        = "dados reais" if is_real else "dados ilustrativos"

    return (
        f"Correlação {strength} e {direction} ({strongest_val:.2f}) entre o retorno de {ticker} "
        f"e {strongest} ({source}). Sensibilidade macro importante para modelagem de risco e alocação."
    )


def render_macro_correlation(
    df: pd.DataFrame | None = None,
    ticker: str = "TICKER",
    price_df: pd.DataFrame | None = None,
) -> None:
    is_real = False

    if df is None or df.empty:
        with st.spinner("Carregando dados macroeconômicos reais..."):
            df, is_real = _fetch_real_macro_df(ticker, price_df)

        if df is None or df.empty:
            df = _demo_macro_df(ticker)
            is_real = False

    section_header_charts(
        "Correlação Macroeconômica",
        f"{ticker} · SELIC | IPCA | USD/BRL"
        + (" · Dados reais" if is_real else " · Dados ilustrativos"),
        C_CYAN,
    )

    if not is_real:
        st.caption(
            "⚠️ API indisponível — exibindo correlações com dados ilustrativos. "
            "Com o backend ativo, os dados de SELIC, IPCA e USD/BRL são reais."
        )

    macro_cols  = [c for c in df.columns if c != "data"]
    ret_col     = f"{ticker} Retorno (%)"
    macro_only  = [c for c in macro_cols if c != ret_col]

    tab1, tab2 = st.tabs(["Série Temporal", "Matriz de Correlação"])

    with tab1:
        fig = go.Figure()
        colors = [C_NEG, C_WARN, C_NEUT, C_POS, C_PURPLE, C_CYAN]

        for i, col in enumerate(macro_only):
            fig.add_trace(go.Scatter(
                x=df["data"], y=df[col],
                name=col.replace(" (%)", "").replace(" (R$)", ""),
                mode="lines",
                line=dict(color=colors[i % len(colors)], width=1.8),
                opacity=0.85,
                hovertemplate=f"<b>{col}</b><br>%{{x|%b %Y}}<br>%{{y:.2f}}<extra></extra>",
            ))

        if ret_col in df.columns:
            fig.add_trace(go.Scatter(
                x=df["data"], y=df[ret_col],
                name=f"{ticker} Retorno",
                mode="lines",
                line=dict(color="#FFFFFF", width=2.2),
                opacity=0.95,
                hovertemplate=f"<b>{ticker}</b><br>%{{x|%b %Y}}<br>%{{y:.2f}}%<extra></extra>",
            ))

        fig.update_layout(**base_layout(
            height=420,
            hovermode="x unified",
            xaxis=dict(gridcolor="rgba(255,255,255,0.02)",
                       tickfont=dict(color=TEXT_MUTED, size=10), type="date"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.03)",
                       tickfont=dict(color=TEXT_MUTED, size=10)),
            legend=LEGEND_RIGHT,
            margin=dict(r=150),
        ))
        fig.update_xaxes(title_text="")
        fig.update_yaxes(title_text="")
        st.plotly_chart(fig, use_container_width=True,
                        config={"toImageButtonOptions": {"format": "png", "scale": 2}})

    with tab2:
        corr   = _correlation_matrix(df)
        labels = corr.columns.tolist()
        text_m = [[f"{corr.loc[r, c]:.2f}" for c in labels] for r in labels]

        fig_c = go.Figure(go.Heatmap(
            z=corr.values.tolist(),
            x=labels, y=labels,
            colorscale=[
                [0.0, "#7f1d1d"], [0.25, "#ef4444"],
                [0.5,  "#1e293b"],
                [0.75, "#059669"], [1.0,  "#064e3b"],
            ],
            zmin=-1, zmax=1,
            text=text_m,
            texttemplate="<b>%{text}</b>",
            textfont=dict(size=10, color="rgba(255,255,255,0.85)"),
            showscale=True,
            colorbar=dict(
                tickfont=dict(color=TEXT_MUTED, size=9),
                bgcolor="rgba(0,0,0,0)",
                bordercolor="rgba(255,255,255,0.05)",
                thickness=10,
            ),
            hovertemplate="<b>%{x} vs %{y}</b><br>r = %{z:.3f}<extra></extra>",
            xgap=2, ygap=2,
        ))
        fig_c.update_layout(**base_layout(
            height=420,
            margin=dict(t=40, b=40, l=120, r=80),
            xaxis=dict(side="bottom", tickfont=dict(color=TEXT_SECONDARY, size=9),
                       gridcolor="rgba(0,0,0,0)"),
            yaxis=dict(tickfont=dict(color=TEXT_SECONDARY, size=9),
                       gridcolor="rgba(0,0,0,0)", autorange="reversed"),
        ))
        fig_c.update_xaxes(title_text="")
        fig_c.update_yaxes(title_text="")
        st.plotly_chart(fig_c, use_container_width=True,
                        config={"toImageButtonOptions": {"format": "png", "scale": 2}})

        if ret_col in corr.columns:
            sens = corr[ret_col].drop(ret_col).reset_index()
            sens.columns = ["Indicador Macro", f"Correlação com {ticker}"]
            sens = sens.sort_values(f"Correlação com {ticker}", key=abs, ascending=False)
            sens["Força"] = sens[f"Correlação com {ticker}"].apply(
                lambda v: "Forte" if abs(v) > 0.5 else ("Moderada" if abs(v) > 0.25 else "Fraca")
            )
            st.dataframe(sens, use_container_width=True, hide_index=True)

    insight_box(_auto_insight(df, ticker, is_real), C_CYAN)
