"""Finance Charts — Detecção de Anomalias de Mercado (Z-Score Estatístico)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .styles import (
    C_NEG, C_NEG2, C_NEUT, C_POS, C_WARN, C_PURPLE, C_CYAN,
    TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY, LEGEND_RIGHT, base_layout,
)
from .utils import (
    insight_box, kpi_card, section_header_charts, _seed,
)


def _detect_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """Z-score anomaly detection on daily returns + volume spikes.

    A day is flagged as anomalous when:
      - |return z-score| > 2.5 (extreme price move vs recent history), OR
      - volume > 3× rolling average AND |return| > 2%
    """
    df = df.copy().reset_index(drop=True)

    returns = df["fechamento"].pct_change()
    ret_mean = returns.rolling(20, min_periods=5).mean()
    ret_std  = returns.rolling(20, min_periods=5).std().replace(0, np.nan)
    z_scores = ((returns - ret_mean) / ret_std).abs().fillna(0)

    vol_ratio = pd.Series(np.ones(len(df)), index=df.index)
    if "volume" in df.columns:
        avg_vol = df["volume"].rolling(20, min_periods=5).mean().replace(0, np.nan)
        vol_ratio = (df["volume"] / avg_vol).fillna(1.0)

    is_anomaly = (z_scores > 2.5) | ((vol_ratio > 3) & (returns.abs() > 0.02))
    is_anomaly = is_anomaly.fillna(False)

    # Normalize score to [0, 1]
    raw_score = z_scores / 5.0 + (vol_ratio - 1.0).clip(lower=0, upper=10) / 10.0
    max_score = raw_score.max()
    anomaly_score = (raw_score / max_score).clip(0, 1) if max_score > 0 else raw_score

    df["is_anomaly"]    = is_anomaly
    df["anomaly_score"] = anomaly_score
    if "volume" not in df.columns:
        df["volume"] = 0

    return df


def _demo_anomaly_data(ticker: str, n: int = 252) -> pd.DataFrame:
    """Synthetic fallback — used only when no real price data is available."""
    np_rng = np.random.RandomState(_seed(ticker) + 20)
    price, prices, volumes = 30.0, [30.0], []
    for _ in range(n - 1):
        prices.append(prices[-1] * (1 + np_rng.normal(0.0003, 0.018)))
    for p in prices:
        volumes.append(np_rng.uniform(1e6, 5e6))

    is_anomaly = np_rng.random(n) < 0.04
    for idx in np.where(is_anomaly)[0]:
        direction = np_rng.choice([-1, 1])
        prices[idx] *= 1 + direction * np_rng.uniform(0.04, 0.10)
        volumes[idx] *= np_rng.uniform(3, 8)

    scores = np_rng.uniform(0, 0.6, n)
    scores[is_anomaly] = np_rng.uniform(0.70, 1.0, is_anomaly.sum())

    dates = pd.date_range(end=pd.Timestamp.today(), periods=n, freq="B")
    return pd.DataFrame({
        "data":          dates,
        "fechamento":    prices,
        "volume":        volumes,
        "anomaly_score": scores,
        "is_anomaly":    is_anomaly,
    })


def _causes(n: int) -> list[str]:
    causes = [
        "Resultado acima/abaixo das estimativas",
        "Movimentação institucional relevante",
        "Notícia ou fato relevante divulgado",
        "Alta volatilidade setorial",
        "Rebalanceamento de índice ou arbitragem",
    ]
    return [causes[i % len(causes)] for i in range(n)]


def _auto_insight(df: pd.DataFrame, is_demo: bool) -> str:
    n_anom  = int(df["is_anomaly"].sum())
    total   = len(df)
    pct     = n_anom / total * 100
    normal  = df[~df["is_anomaly"]]
    anomaly = df[df["is_anomaly"]]
    high_vol = (
        anomaly["volume"].mean() / normal["volume"].mean()
        if n_anom > 0 and len(normal) > 0 and normal["volume"].mean() > 0
        else 1.0
    )
    suffix = " (dados ilustrativos)" if is_demo else ""
    if pct < 3:
        return (
            f"Apenas {n_anom} eventos anômalos detectados ({pct:.1f}% dos pregões){suffix}. "
            f"Volume médio nos eventos é {high_vol:.1f}× acima do normal. "
            "Comportamento consistente com padrão de mercado."
        )
    return (
        f"{n_anom} anomalias detectadas ({pct:.1f}% dos pregões){suffix}. "
        f"Volume médio {high_vol:.1f}× superior ao normal. "
        "Recomenda-se investigar catalisadores fundamentalistas nos eventos destacados."
    )


def render_anomaly_chart(
    df: pd.DataFrame | None = None,
    ticker: str = "TICKER",
) -> None:
    is_demo = df is None or df.empty

    if is_demo:
        df = _demo_anomaly_data(ticker)
        section_header_charts(
            "Detecção de Anomalias de Mercado",
            f"{ticker} · Z-Score Estatístico — Anomalias de Preço e Volume (Demonstração)",
            C_NEG,
        )
        st.caption(
            "⚠️ Dados de preço indisponíveis para este ticker — exibindo dados ilustrativos. "
            "Com histórico real, a detecção usa Z-Score sobre retornos diários e spikes de volume."
        )
    else:
        # Real z-score detection
        if "is_anomaly" not in df.columns:
            df = _detect_anomalies(df)
        section_header_charts(
            "Detecção de Anomalias de Mercado",
            f"{ticker} · Z-Score sobre Retornos Diários | Spike de Volume",
            C_NEG,
        )

    normal    = df[~df["is_anomaly"]]
    anomalous = df[df["is_anomaly"]]
    n_anom    = len(anomalous)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(kpi_card("Anomalias Detectadas", str(n_anom),
                             f"{n_anom / len(df) * 100:.1f}% dos pregões",
                             n_anom < 15, C_NEG, "◈"), unsafe_allow_html=True)
    with c2:
        avg_score = float(anomalous["anomaly_score"].mean()) if n_anom > 0 else 0.0
        st.markdown(kpi_card("Score Médio", f"{avg_score:.2f}",
                             "Z-Score normalizado", accent=C_WARN, icon="≈"), unsafe_allow_html=True)
    with c3:
        vol_ratio = (
            float(anomalous["volume"].mean() / normal["volume"].mean())
            if n_anom > 0 and len(normal) > 0 and normal["volume"].mean() > 0
            else 1.0
        )
        st.markdown(kpi_card("Vol. Anômalo", f"{vol_ratio:.1f}×",
                             "vs Volume Normal", vol_ratio < 3, C_PURPLE, "⊞"), unsafe_allow_html=True)
    with c4:
        last_score = float(df["anomaly_score"].iloc[-1])
        st.markdown(kpi_card("Score Atual", f"{last_score:.2f}",
                             "Último pregão", last_score < 0.5, C_CYAN, "◎"), unsafe_allow_html=True)

    st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=normal["data"], y=normal["fechamento"],
        mode="lines",
        name="Preço Normal",
        line=dict(color="#9CA3AF", width=1.4),
        fill="tozeroy",
        fillcolor="rgba(156,163,175,0.04)",
        hovertemplate="%{x|%d/%m/%Y}<br>R$ %{y:.2f}<extra></extra>",
    ))

    if n_anom > 0:
        anomaly_sizes = (anomalous["anomaly_score"] * 18 + 8).tolist()
        fig.add_trace(go.Scatter(
            x=anomalous["data"], y=anomalous["fechamento"],
            mode="markers",
            name="Anomalia Detectada",
            marker=dict(
                color=anomalous["anomaly_score"].tolist(),
                colorscale=[[0, C_WARN], [0.5, "#F97316"], [1.0, C_NEG]],
                size=anomaly_sizes,
                opacity=0.9,
                line=dict(color="rgba(239,68,68,0.4)", width=2),
                showscale=True,
                colorbar=dict(
                    title=dict(text="Score", font=dict(color=TEXT_MUTED, size=9)),
                    tickfont=dict(color=TEXT_MUTED, size=8),
                    bgcolor="rgba(0,0,0,0)",
                    bordercolor="rgba(255,255,255,0.05)",
                    thickness=8, len=0.5, x=1.01,
                ),
            ),
            customdata=anomalous["anomaly_score"].tolist(),
            hovertemplate=(
                "<b>⚠ Anomalia</b><br>"
                "%{x|%d/%m/%Y}<br>"
                "R$ %{y:.2f}<br>"
                "Score: %{customdata:.3f}<extra></extra>"
            ),
        ))

        for _, row in anomalous.iterrows():
            fig.add_vrect(
                x0=row["data"] - pd.Timedelta(days=1),
                x1=row["data"] + pd.Timedelta(days=1),
                fillcolor="rgba(239,68,68,0.06)",
                line_width=0,
                layer="below",
            )

    fig.update_layout(**base_layout(
        height=460,
        hovermode="closest",
        yaxis=dict(tickprefix="R$ ", gridcolor="rgba(255,255,255,0.03)",
                   tickfont=dict(color=TEXT_MUTED, size=10)),
        xaxis=dict(gridcolor="rgba(255,255,255,0.02)",
                   tickfont=dict(color=TEXT_MUTED, size=10), type="date"),
        legend=LEGEND_RIGHT,
        margin=dict(r=150),
    ))
    fig.update_xaxes(title_text="")
    fig.update_yaxes(title_text="")
    st.plotly_chart(fig, use_container_width=True,
                    config={"toImageButtonOptions": {"format": "png", "scale": 2}})

    if n_anom > 0:
        st.markdown(
            f"<div style='font-size:0.68rem;font-weight:700;text-transform:uppercase;"
            f"letter-spacing:0.08em;color:{TEXT_MUTED};margin-bottom:0.4rem;"
            f"font-family:Inter,sans-serif;'>⚠ Principais Anomalias</div>",
            unsafe_allow_html=True,
        )
        top_anom = anomalous.nlargest(5, "anomaly_score").copy()
        top_anom["Possível Causa"] = _causes(len(top_anom))
        display_df = top_anom[["data", "fechamento", "anomaly_score", "Possível Causa"]].copy()
        display_df.columns = ["Data", "Preço (R$)", "Score", "Possível Causa"]
        display_df["Data"] = pd.to_datetime(display_df["Data"]).dt.strftime("%d/%m/%Y")
        display_df["Preço (R$)"] = display_df["Preço (R$)"].map("R$ {:.2f}".format)
        display_df["Score"]      = display_df["Score"].map("{:.3f}".format)
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    insight_box(_auto_insight(df, is_demo), C_NEG)
