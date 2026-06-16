"""Finance — Compare Assets Page."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from config import TICKER_UNIVERSE
from utils.api import fetch, to_float
from utils.charts import correlation_heatmap, performance_chart, risk_return_scatter
from utils.ui import render_dark_table, section_header, apply_period_filter


def render() -> None:
    section_header("Comparar Ativos", "#ec4899")

    c1, c2 = st.columns([3, 1])
    with c1:
        selected = st.multiselect(
            "Selecione 2–5 ativos",
            options=list(TICKER_UNIVERSE.keys()),
            default=["PETR4", "VALE3", "ITUB4", "WEGE3"],
            format_func=lambda t: f"{t} — {TICKER_UNIVERSE[t]}",
            max_selections=5,
            key="cmp_assets",
        )
    with c2:
        period = st.selectbox("Período", ["1y", "6mo", "3mo", "1mo"], key="cmp_period")

    if len(selected) < 2:
        st.info("Selecione pelo menos 2 ativos para comparar.")
        return

    tickers_param = ",".join(selected)

    with st.spinner(f"Comparando {', '.join(selected)}..."):
        cdata = fetch("/compare", {"tickers": tickers_param, "periodo": period}, timeout=120)

    if not cdata or not cdata.get("metrics"):
        st.error("Dados de comparação indisponíveis. Verifique a conectividade com a API.")
        return

    metrics_raw = cdata["metrics"]
    corr_raw = cdata.get("correlacao", {})
    perf_raw = cdata.get("performance", [])

    # ── KPI Cards ─────────────────────────────────────────────────
    section_header("Métricas Principais", "#3b82f6")
    kpi_cols = st.columns(len(metrics_raw))
    for col, m in zip(kpi_cols, metrics_raw):
        ret = to_float(m.get("retorno_acumulado"))
        vol = to_float(m.get("volatilidade_anual"))
        sharpe = to_float(m.get("sharpe"))
        price = to_float(m.get("preco_atual"))
        ret_str = f"{ret:+.1f}%" if ret is not None else "—"
        price_str = f"R$ {price:.2f}" if price else "—"
        vol_str = f"Vol {vol:.1f}%" if vol else ""
        sharpe_str = f"Sharpe {sharpe:.2f}" if sharpe else ""
        with col:
            st.markdown(
                f"<div style='background:#111827;border:1px solid rgba(255,255,255,0.05);"
                f"border-top:2px solid #ec4899;border-radius:10px;padding:1rem;text-align:center;'>"
                f"<div style='font-size:1rem;font-weight:800;color:#f1f5f9;"
                f"font-family:\"JetBrains Mono\",monospace;'>{m['ticker']}</div>"
                f"<div style='font-size:0.68rem;color:#475569;margin:2px 0 8px;font-family:Inter,sans-serif;'>"
                f"{m.get('setor','')}</div>"
                f"<div style='font-size:1.3rem;font-weight:700;color:{'#10b981' if (ret or 0)>=0 else '#ef4444'};"
                f"font-family:\"JetBrains Mono\",monospace;'>{ret_str}</div>"
                f"<div style='font-size:0.78rem;color:#94a3b8;font-family:\"JetBrains Mono\",monospace;"
                f"margin-top:4px;'>{price_str}</div>"
                f"<div style='font-size:0.68rem;color:#475569;margin-top:2px;font-family:Inter,sans-serif;'>"
                f"{vol_str}{' · ' if vol_str and sharpe_str else ''}{sharpe_str}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)

    # ── Performance Chart ──────────────────────────────────────────
    if perf_raw:
        perf_dfs = []
        for series in perf_raw:
            if series.get("pontos"):
                df_s = pd.DataFrame(series["pontos"])
                df_s["data"] = pd.to_datetime(df_s["data"])
                df_s = apply_period_filter(df_s)
                df_s["ticker"] = series["ticker"]
                perf_dfs.append(df_s)
        if perf_dfs:
            df_perf = pd.concat(perf_dfs, ignore_index=True)
            section_header("Desempenho Acumulado (Base 100)", "#10b981")
            st.plotly_chart(performance_chart(df_perf), use_container_width=True)

    # ── Risk Metrics Table ─────────────────────────────────────────
    section_header("Métricas de Risco", "#f59e0b")
    risk_cols = ["ticker", "setor", "preco_atual", "retorno_acumulado", "cagr",
                 "volatilidade_anual", "sharpe", "sortino", "max_drawdown", "beta", "var_95"]
    risk_labels = {
        "ticker": "Ticker", "setor": "Setor", "preco_atual": "Preço (R$)",
        "retorno_acumulado": "Retorno %", "cagr": "CAGR %",
        "volatilidade_anual": "Vol. Anual %", "sharpe": "Sharpe",
        "sortino": "Sortino", "max_drawdown": "Max Drawdown %",
        "beta": "Beta", "var_95": "VaR 95%",
    }
    df_risk = pd.DataFrame([{k: m.get(k) for k in risk_cols} for m in metrics_raw])
    df_risk = df_risk.rename(columns=risk_labels)
    fmt_cols = ["Preço (R$)", "Retorno %", "CAGR %", "Vol. Anual %",
                "Sharpe", "Sortino", "Max Drawdown %", "Beta", "VaR 95%"]

    df_risk_disp = df_risk.reset_index(drop=True)
    cell_colors_risk: dict[tuple[int, str], str] = {}
    for col in ["Retorno %", "CAGR %", "Max Drawdown %"]:
        if col in df_risk_disp.columns:
            for i, v in enumerate(df_risk_disp[col]):
                if isinstance(v, (int, float)):
                    cell_colors_risk[(i, col)] = "#10b981" if v >= 0 else "#ef4444"
    for c in fmt_cols:
        if c in df_risk_disp.columns:
            df_risk_disp[c] = df_risk_disp[c].apply(
                lambda v: f"{v:.2f}" if isinstance(v, (int, float)) else "—"
            )
    render_dark_table(df_risk_disp, cell_colors=cell_colors_risk)

    # ── Scatter + Heatmap ──────────────────────────────────────────
    col_s, col_h = st.columns(2, gap="medium")

    with col_s:
        section_header("Risco × Retorno", "#a855f7")
        scatter_data = [
            {
                "ticker": m["ticker"],
                "Retorno (%)": to_float(m.get("retorno_acumulado")),
                "Volatilidade (%)": to_float(m.get("volatilidade_anual")),
                "Sharpe": to_float(m.get("sharpe")) or 0,
                "Setor": m.get("setor", ""),
            }
            for m in metrics_raw
            if m.get("retorno_acumulado") is not None and m.get("volatilidade_anual") is not None
        ]
        if scatter_data:
            st.plotly_chart(risk_return_scatter(pd.DataFrame(scatter_data)), use_container_width=True)

    with col_h:
        section_header("Matriz de Correlação", "#06b6d4")
        if corr_raw and len(corr_raw) >= 2:
            tickers_corr = list(corr_raw.keys())
            matrix = [[corr_raw[t1].get(t2) for t2 in tickers_corr] for t1 in tickers_corr]
            st.plotly_chart(correlation_heatmap(tickers_corr, matrix), use_container_width=True)

    # ── Technical Indicators ───────────────────────────────────────
    if any(m.get("rsi_14") is not None for m in metrics_raw):
        section_header("Indicadores Técnicos", "#10b981")
        tech_cols = ["ticker", "preco_atual", "rsi_14", "ma_20", "ma_50", "ma_200"]
        tech_labels = {
            "ticker": "Ticker", "preco_atual": "Preço (R$)",
            "rsi_14": "RSI(14)", "ma_20": "MA(20)", "ma_50": "MA(50)", "ma_200": "MA(200)",
        }
        df_tech = pd.DataFrame([{k: m.get(k) for k in tech_cols} for m in metrics_raw])
        df_tech = df_tech.rename(columns=tech_labels)

        df_tech_disp = df_tech.reset_index(drop=True)
        cell_colors_rsi: dict[tuple[int, str], str] = {}
        if "RSI(14)" in df_tech_disp.columns:
            for i, v in enumerate(df_tech_disp["RSI(14)"]):
                if isinstance(v, (int, float)):
                    if v >= 70:
                        cell_colors_rsi[(i, "RSI(14)")] = "#ef4444"
                    elif v <= 30:
                        cell_colors_rsi[(i, "RSI(14)")] = "#10b981"
        num_cols = ["Preço (R$)", "RSI(14)", "MA(20)", "MA(50)", "MA(200)"]
        for c in num_cols:
            if c in df_tech_disp.columns:
                df_tech_disp[c] = df_tech_disp[c].apply(
                    lambda v: f"{v:.2f}" if isinstance(v, (int, float)) else "—"
                )
        render_dark_table(df_tech_disp, cell_colors=cell_colors_rsi)
        st.caption("RSI > 70 = Sobrecomprado (vermelho) · RSI < 30 = Sobrevendido (verde)")
