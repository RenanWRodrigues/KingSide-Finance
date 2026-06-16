"""Finance Dashboard — Plotly Chart Factories."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import CHART_LAYOUT, COLORS, PALETTE, SECTOR_COLORS


def _base_layout(**overrides) -> dict:
    layout = dict(CHART_LAYOUT)
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


def candlestick_with_indicators(
    df: pd.DataFrame,
    ticker: str,
    show_volume: bool = True,
    show_rsi: bool = True,
    show_macd: bool = False,
    ma_periods: list[int] | None = None,
    precomputed: dict[str, pd.Series] | None = None,
) -> go.Figure:
    """Professional candlestick chart with MA, RSI, Volume overlays."""
    ma_periods = ma_periods or [20, 50, 200]
    precomputed = precomputed or {}

    row_count = 2 + (1 if show_rsi else 0) + (1 if show_macd else 0)
    row_heights = [0.55, 0.15]
    if show_rsi:
        row_heights.append(0.15)
    if show_macd:
        row_heights.append(0.15)

    subplot_titles = [f"{ticker} — Preço", "Volume"]
    if show_rsi:
        subplot_titles.append("RSI(14)")
    if show_macd:
        subplot_titles.append("MACD")

    specs = [[{"type": "candlestick"}]] + [[{"type": "bar"}]] + [[{"type": "scatter"}]] * (row_count - 2)

    fig = make_subplots(
        rows=row_count,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.10,
        row_heights=row_heights,
        subplot_titles=subplot_titles,
    )

    # ── Candlestick ──────────────────────────────────────────────
    fig.add_trace(
        go.Candlestick(
            x=df["data"],
            open=df["abertura"],
            high=df["maxima"],
            low=df["minima"],
            close=df["fechamento"],
            name=ticker,
            increasing=dict(fillcolor="#10b981", line=dict(color="#10b981", width=1)),
            decreasing=dict(fillcolor="#ef4444", line=dict(color="#ef4444", width=1)),
            whiskerwidth=0.4,
        ),
        row=1, col=1,
    )

    # ── Moving Averages ──────────────────────────────────────────
    ma_colors = ["#3b82f6", "#f59e0b", "#8b5cf6"]
    for period, color in zip(ma_periods, ma_colors):
        if len(df) >= period:
            key = f"ma{period}"
            ma = precomputed[key] if key in precomputed else df["fechamento"].rolling(period).mean()
            fig.add_trace(
                go.Scatter(
                    x=df["data"], y=ma,
                    mode="lines",
                    name=f"MA{period}",
                    line=dict(color=color, width=1.2, dash="solid"),
                    opacity=0.8,
                ),
                row=1, col=1,
            )

    # ── Bollinger Bands ──────────────────────────────────────────
    if len(df) >= 20:
        ma20  = precomputed["ma20"]  if "ma20"  in precomputed else df["fechamento"].rolling(20).mean()
        std20 = precomputed["std20"] if "std20" in precomputed else df["fechamento"].rolling(20).std()
        upper_bb = ma20 + 2 * std20
        lower_bb = ma20 - 2 * std20
        fig.add_trace(
            go.Scatter(
                x=pd.concat([df["data"], df["data"].iloc[::-1]]),
                y=pd.concat([upper_bb, lower_bb.iloc[::-1]]),
                fill="toself",
                fillcolor="rgba(59,130,246,0.06)",
                line=dict(color="rgba(255,255,255,0)"),
                name="BB(20,2)",
                showlegend=True,
            ),
            row=1, col=1,
        )

    # ── Volume ───────────────────────────────────────────────────
    if "volume" in df.columns:
        colors = [
            "#10b981" if c >= o else "#ef4444"
            for c, o in zip(df["fechamento"], df["abertura"])
        ]
        fig.add_trace(
            go.Bar(
                x=df["data"], y=df["volume"],
                name="Volume",
                marker=dict(color=colors, opacity=0.7),
                showlegend=False,
            ),
            row=2, col=1,
        )

    # ── RSI ──────────────────────────────────────────────────────
    if show_rsi:
        rsi_row = 3
        if len(df) >= 15:
            if "rsi" in precomputed:
                rsi = precomputed["rsi"]
            else:
                delta = df["fechamento"].diff()
                gain = delta.clip(lower=0).rolling(14).mean()
                loss = (-delta.clip(upper=0)).rolling(14).mean()
                rs = gain / loss.replace(0, float("nan"))
                rsi = 100 - 100 / (1 + rs)
            fig.add_trace(
                go.Scatter(
                    x=df["data"], y=rsi,
                    name="RSI(14)",
                    line=dict(color="#a855f7", width=1.5),
                    fill="tozeroy",
                    fillcolor="rgba(168,85,247,0.06)",
                ),
                row=rsi_row, col=1,
            )
            fig.add_hline(y=70, line_dash="dot", line_color="#ef4444", opacity=0.5, row=rsi_row, col=1)
            fig.add_hline(y=30, line_dash="dot", line_color="#10b981", opacity=0.5, row=rsi_row, col=1)
            fig.update_yaxes(range=[0, 100], row=rsi_row, col=1)

    # ── MACD ─────────────────────────────────────────────────────
    if show_macd:
        macd_row = rsi_row + 1 if show_rsi else 3
        if len(df) >= 26:
            ema12 = df["fechamento"].ewm(span=12).mean()
            ema26 = df["fechamento"].ewm(span=26).mean()
            macd_line = ema12 - ema26
            signal = macd_line.ewm(span=9).mean()
            hist = macd_line - signal
            hist_colors = ["#10b981" if v >= 0 else "#ef4444" for v in hist]
            fig.add_trace(
                go.Bar(x=df["data"], y=hist, name="MACD Hist",
                       marker=dict(color=hist_colors, opacity=0.7), showlegend=False),
                row=macd_row, col=1,
            )
            fig.add_trace(
                go.Scatter(x=df["data"], y=macd_line, name="MACD",
                           line=dict(color="#3b82f6", width=1.3)),
                row=macd_row, col=1,
            )
            fig.add_trace(
                go.Scatter(x=df["data"], y=signal, name="Signal",
                           line=dict(color="#f59e0b", width=1.3, dash="dash")),
                row=macd_row, col=1,
            )

    layout = _base_layout(
        height=620 + (100 if show_rsi else 0) + (100 if show_macd else 0),
        showlegend=True,
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
    )
    fig.update_layout(**layout)

    row_labels = {1: "Preço (R$)", 2: "Volume"}
    if show_rsi:
        row_labels[3] = "RSI"
    if show_macd:
        row_labels[3 + (1 if show_rsi else 0)] = "MACD"

    # Blanket clear first — catches shared/secondary axes not covered by the loop
    fig.update_xaxes(title_text="")
    fig.update_yaxes(title_text="")

    for i in range(1, row_count + 1):
        fig.update_xaxes(
            gridcolor="rgba(255,255,255,0.035)",
            linecolor="rgba(255,255,255,0.06)",
            tickfont=dict(color="#64748b", size=10),
            row=i, col=1,
        )
        fig.update_yaxes(
            title_text=row_labels.get(i, ""),
            gridcolor="rgba(255,255,255,0.035)",
            linecolor="rgba(255,255,255,0.06)",
            tickfont=dict(color="#64748b", size=10),
            row=i, col=1,
        )

    return fig


def performance_chart(df_perf: pd.DataFrame, height: int = 420) -> go.Figure:
    """Normalized performance chart with base 100."""
    fig = go.Figure()
    tickers = df_perf["ticker"].unique()

    for i, ticker in enumerate(tickers):
        df_t = df_perf[df_perf["ticker"] == ticker].sort_values("data")
        color = PALETTE[i % len(PALETTE)]
        last_val = df_t["normalizado"].iloc[-1] if len(df_t) > 0 else 100
        delta_str = f"+{last_val - 100:.1f}%" if last_val >= 100 else f"{last_val - 100:.1f}%"
        fig.add_trace(
            go.Scatter(
                x=df_t["data"], y=df_t["normalizado"],
                name=f"{ticker} ({delta_str})",
                mode="lines",
                line=dict(color=color, width=2),
                fill="tozeroy",
                fillcolor=f"rgba{tuple(int(color.lstrip('#')[i:i+2],16) for i in (0,2,4)) + (0.04,)}",
                hovertemplate=f"<b>{ticker}</b><br>%{{x|%d/%m/%Y}}<br>Índice: %{{y:.1f}}<extra></extra>",
            )
        )

    fig.add_hline(y=100, line_dash="dot", line_color="rgba(255,255,255,0.2)", opacity=0.6)
    layout = _base_layout(
        height=height,
        hovermode="x unified",
        yaxis_title="Índice (base 100)",
    )
    fig.update_layout(**layout)
    fig.update_xaxes(title_text="")
    fig.update_yaxes(title_text="Índice (base 100)")
    return fig


def correlation_heatmap(tickers: list[str], matrix: list[list[float | None]]) -> go.Figure:
    text = [[f"{v:.2f}" if v is not None else "" for v in row] for row in matrix]
    fig = go.Figure(
        go.Heatmap(
            z=matrix,
            x=tickers, y=tickers,
            colorscale=[
                [0.0, "#ef4444"], [0.25, "#dc2626"],
                [0.5, "#1e293b"],
                [0.75, "#059669"], [1.0, "#10b981"],
            ],
            zmin=-1, zmax=1,
            text=text,
            texttemplate="%{text}",
            textfont=dict(size=12, color="#f1f5f9"),
            showscale=True,
            colorbar=dict(
                tickfont=dict(color="#64748b", size=10),
                bgcolor="rgba(0,0,0,0)",
                bordercolor="rgba(255,255,255,0.06)",
            ),
        )
    )
    layout = _base_layout(height=380, margin=dict(t=30, b=30, l=60, r=40))
    fig.update_layout(**layout)
    fig.update_xaxes(title_text="")
    fig.update_yaxes(title_text="")
    return fig


def risk_return_scatter(df_scatter: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for i, row in df_scatter.iterrows():
        color = SECTOR_COLORS.get(row.get("Setor", ""), PALETTE[i % len(PALETTE)])
        size = max(abs(row.get("Sharpe", 0) or 0) * 14 + 10, 12)
        fig.add_trace(
            go.Scatter(
                x=[row["Volatilidade (%)"]],
                y=[row["Retorno (%)"]],
                mode="markers+text",
                text=[row["ticker"]],
                textposition="top center",
                textfont=dict(size=11, color="#f1f5f9"),
                marker=dict(
                    color=color, size=size, opacity=0.85,
                    line=dict(color="rgba(255,255,255,0.2)", width=1),
                ),
                name=row.get("Setor", row["ticker"]),
                hovertemplate=(
                    f"<b>{row['ticker']}</b><br>"
                    f"Volatilidade: {row['Volatilidade (%)']:.1f}%<br>"
                    f"Retorno: {row['Retorno (%)']:+.1f}%<br>"
                    f"Sharpe: {row.get('Sharpe', 0):.2f}<extra></extra>"
                ),
                showlegend=False,
            )
        )
    layout = _base_layout(
        height=380,
        xaxis_title="Volatilidade Anual (%)",
        yaxis_title="Retorno Acumulado (%)",
        hovermode="closest",
    )
    fig.update_layout(**layout)
    fig.add_hline(y=0, line_dash="dot", line_color="rgba(255,255,255,0.15)", opacity=0.5)
    fig.update_xaxes(title_text="Volatilidade Anual (%)")
    fig.update_yaxes(title_text="Retorno Acumulado (%)")
    return fig


def macro_line_chart(df: pd.DataFrame, indicator: str, height: int = 380) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["data"], y=df["valor"],
            mode="lines",
            name=indicator.upper(),
            line=dict(color="#3b82f6", width=2),
            fill="tozeroy",
            fillcolor="rgba(59,130,246,0.06)",
            hovertemplate=f"<b>{indicator.upper()}</b><br>%{{x|%d/%m/%Y}}<br>%{{y:.4f}}<extra></extra>",
        )
    )
    layout = _base_layout(height=height, hovermode="x unified")
    fig.update_layout(**layout)
    fig.update_xaxes(title_text="")
    fig.update_yaxes(title_text="")
    return fig


def ranking_bar_chart(df: pd.DataFrame, title: str, value_col: str = "valor") -> go.Figure:
    df_sorted = df.sort_values(value_col, ascending=True).tail(15)
    colors = [
        SECTOR_COLORS.get(s, "#3b82f6") for s in df_sorted.get("setor", [""] * len(df_sorted))
    ]
    fig = go.Figure(
        go.Bar(
            x=df_sorted[value_col],
            y=df_sorted["ticker"],
            orientation="h",
            marker=dict(
                color=colors,
                opacity=0.85,
                line=dict(color="rgba(255,255,255,0.1)", width=0.5),
            ),
            text=[f"{v:.1f}%" for v in df_sorted[value_col]],
            textposition="outside",
            textfont=dict(color="#94a3b8", size=11),
            hovertemplate="<b>%{y}</b><br>%{x:.2f}%<extra></extra>",
        )
    )
    layout = _base_layout(
        title=title,
        height=420,
        margin=dict(t=40, b=20, l=70, r=60),
        xaxis_title="",
        yaxis_title="",
    )
    fig.update_layout(**layout)
    fig.update_xaxes(title_text="")
    fig.update_yaxes(title_text="")
    return fig


def market_treemap(data: list[dict]) -> go.Figure:
    """Sector heatmap treemap — Finviz style."""
    labels, parents, values, customdata, colors = [], [], [], [], []
    sector_data: dict[str, dict] = {}

    for item in data:
        sector = item.get("setor", "Outros")
        change = item.get("change_pct", 0.0) or 0.0
        if sector not in sector_data:
            sector_data[sector] = {"total_vol": 0, "changes": []}
        sector_data[sector]["total_vol"] += abs(item.get("market_cap", 1) or 1)
        sector_data[sector]["changes"].append(change)

    # Add root
    labels.append("B3")
    parents.append("")
    values.append(0)
    customdata.append(["", 0])
    colors.append(0)

    for sector, sdata in sector_data.items():
        avg_change = sum(sdata["changes"]) / len(sdata["changes"])
        labels.append(sector)
        parents.append("B3")
        values.append(sdata["total_vol"])
        customdata.append([sector, avg_change])
        colors.append(avg_change)

    for item in data:
        label = item.get("ticker", "")
        sector = item.get("setor", "Outros")
        change = item.get("change_pct", 0.0) or 0.0
        price = item.get("preco", 0.0) or 0.0
        labels.append(label)
        parents.append(sector)
        values.append(abs(item.get("market_cap", 1) or 1))
        customdata.append([label, change, price])
        colors.append(change)

    max_abs = max(abs(c) for c in colors if c is not None) or 5
    normalized = [c / max_abs for c in colors]

    fig = go.Figure(
        go.Treemap(
            labels=labels,
            parents=parents,
            values=values,
            customdata=customdata,
            marker=dict(
                colors=normalized,
                colorscale=[
                    [0.0, "#7f1d1d"], [0.35, "#ef4444"],
                    [0.5, "#1e293b"],
                    [0.65, "#059669"], [1.0, "#064e3b"],
                ],
                cmin=-1, cmax=1,
                showscale=True,
                colorbar=dict(
                    tickvals=[-1, -0.5, 0, 0.5, 1],
                    ticktext=[
                        f"-{max_abs:.1f}%", f"-{max_abs/2:.1f}%", "0%",
                        f"+{max_abs/2:.1f}%", f"+{max_abs:.1f}%",
                    ],
                    tickfont=dict(color="#64748b", size=9),
                    bgcolor="rgba(0,0,0,0)",
                    bordercolor="rgba(255,255,255,0.06)",
                ),
                line=dict(color="#080d1a", width=1),
            ),
            texttemplate="<b>%{label}</b><br>%{customdata[1]:.1f}%",
            textfont=dict(color="#f1f5f9", size=11),
            hovertemplate="<b>%{label}</b><br>Variação: %{customdata[1]:.2f}%<extra></extra>",
            tiling=dict(packing="squarify"),
        )
    )
    layout = _base_layout(height=520, margin=dict(t=20, b=10, l=10, r=10))
    fig.update_layout(**layout)
    return fig


def score_gauge(score: float, ticker: str) -> go.Figure:
    color = "#10b981" if score >= 70 else ("#f59e0b" if score >= 50 else "#ef4444")
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            title=dict(text=ticker, font=dict(color="#94a3b8", size=12)),
            gauge=dict(
                axis=dict(range=[0, 100], tickfont=dict(color="#475569", size=9)),
                bar=dict(color=color, thickness=0.25),
                bgcolor="rgba(255,255,255,0.04)",
                bordercolor="rgba(255,255,255,0.08)",
                steps=[
                    dict(range=[0, 30], color="rgba(239,68,68,0.08)"),
                    dict(range=[30, 70], color="rgba(245,158,11,0.06)"),
                    dict(range=[70, 100], color="rgba(16,185,129,0.08)"),
                ],
                threshold=dict(
                    line=dict(color="rgba(255,255,255,0.3)", width=2),
                    thickness=0.75,
                    value=score,
                ),
            ),
            number=dict(suffix="/100", font=dict(color=color, size=24)),
        )
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=180,
        margin=dict(t=30, b=10, l=20, r=20),
        font=dict(family="Inter, sans-serif"),
    )
    return fig
