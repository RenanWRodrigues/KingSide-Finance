"""Investment Insights — quantitative scoring & ranking API."""
from __future__ import annotations

import math
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.core.cache import cached
from app.core.logging import get_logger
from app.services.financial_data import YFinanceService

logger = get_logger(__name__)
router = APIRouter(prefix="/investment", tags=["investment-insights"])


# ── Schemas ───────────────────────────────────────────────────

class SubScores(BaseModel):
    momentum: float
    trend: float
    risk: float
    rsi: float


class InvestmentScore(BaseModel):
    ticker: str
    setor: str | None = None
    score: float
    signal: str
    sub_scores: SubScores
    total_return_1y: float | None = None
    volatility_annual: float | None = None
    sharpe_approx: float | None = None
    upside_estimate: float | None = None


class InsightsResponse(BaseModel):
    period: str
    assets_analyzed: int
    top_picks: list[InvestmentScore]
    all_scores: list[InvestmentScore]


# ── Helpers ───────────────────────────────────────────────────

_SIGNAL_THRESHOLDS = [(75, "Strong Buy"), (60, "Buy"), (40, "Neutral"), (25, "Sell")]


def _to_signal(score: float) -> str:
    for threshold, label in _SIGNAL_THRESHOLDS:
        if score >= threshold:
            return label
    return "Strong Sell"


def _compute_score(closes: list[float]) -> dict:
    if len(closes) < 20:
        return {"score": 50.0, "momentum": 50.0, "trend": 50.0, "risk": 50.0, "rsi": 50.0}

    import statistics

    # Momentum
    ret_1m = (closes[-1] / closes[max(0, len(closes)-21)] - 1) * 100 if len(closes) >= 21 else 0
    ret_3m = (closes[-1] / closes[max(0, len(closes)-63)] - 1) * 100 if len(closes) >= 63 else 0
    ret_1y = (closes[-1] / closes[0] - 1) * 100
    momentum = max(0.0, min(100.0, 50 + (ret_1m * 0.2 + ret_3m * 0.4 + ret_1y * 0.4) * 0.7))

    # Trend
    ma20 = statistics.mean(closes[-20:]) if len(closes) >= 20 else None
    ma50 = statistics.mean(closes[-50:]) if len(closes) >= 50 else None
    ma200 = statistics.mean(closes[-200:]) if len(closes) >= 200 else None
    price = closes[-1]
    trend = 50.0
    if ma20:
        trend += 15 if price > ma20 else -15
    if ma50:
        trend += 20 if price > ma50 else -20
    if ma200:
        trend += 15 if price > ma200 else -15
    if ma20 and ma50:
        trend += 10 if ma20 > ma50 else -10
    trend = max(0.0, min(100.0, trend))

    # Volatility / Risk
    diffs = [closes[i] / closes[i-1] - 1 for i in range(1, len(closes))]
    vol = statistics.stdev(diffs) * math.sqrt(252) * 100 if len(diffs) >= 2 else 30
    risk = max(0.0, min(100.0, 100 - vol * 1.2))

    # RSI
    gains = [max(0, closes[i] - closes[i-1]) for i in range(1, len(closes))]
    losses = [max(0, closes[i-1] - closes[i]) for i in range(1, len(closes))]
    avg_gain = statistics.mean(gains[-14:]) if len(gains) >= 14 else 0.01
    avg_loss = statistics.mean(losses[-14:]) if len(losses) >= 14 else 0.01
    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    rsi = 100 - 100 / (1 + rs)
    rsi_score = max(0.0, 100 - abs(rsi - 50) * 1.5)

    composite = momentum * 0.30 + trend * 0.30 + risk * 0.20 + rsi_score * 0.20

    # Sharpe approx
    mean_r = statistics.mean(diffs) if diffs else 0
    std_r = statistics.stdev(diffs) if len(diffs) >= 2 else 0.01
    risk_free_daily = 0.000417
    sharpe = (mean_r - risk_free_daily) / std_r * math.sqrt(252) if std_r > 0 else 0

    return {
        "score": round(composite, 2),
        "momentum": round(momentum, 2),
        "trend": round(trend, 2),
        "risk": round(risk, 2),
        "rsi": round(rsi_score, 2),
        "total_return_1y": round(ret_1y, 2),
        "volatility": round(vol, 2),
        "sharpe": round(sharpe, 3),
    }


_B3_TICKERS = [
    "PETR4.SA", "VALE3.SA", "ITUB4.SA", "WEGE3.SA", "BBAS3.SA",
    "ABEV3.SA", "RENT3.SA", "EMBR3.SA", "TOTS3.SA", "RADL3.SA",
    "EGIE3.SA", "RAIL3.SA", "SUZB3.SA", "PRIO3.SA", "BBSE3.SA",
]

_SECTOR_MAP = {
    "PETR4": "Petróleo e Gás", "VALE3": "Mineração", "ITUB4": "Bancos",
    "WEGE3": "Bens Industriais", "BBAS3": "Bancos", "ABEV3": "Bebidas",
    "RENT3": "Locação de Veículos", "EMBR3": "Bens Industriais",
    "TOTS3": "Tecnologia", "RADL3": "Saúde", "EGIE3": "Energia Elétrica",
    "RAIL3": "Logística", "SUZB3": "Papel e Celulose",
    "PRIO3": "Petróleo e Gás", "BBSE3": "Seguros",
}


# ── Endpoints ─────────────────────────────────────────────────

@router.get("/insights", response_model=InsightsResponse, summary="Investment Insights Ranking")
@cached(ttl=3600)
async def get_investment_insights(
    period: Annotated[str, Query(description="Analysis period: 1y, 6mo, 3mo")] = "1y",
    top_n: Annotated[int, Query(ge=1, le=35)] = 10,
) -> InsightsResponse:
    svc = YFinanceService()
    all_scores: list[InvestmentScore] = []

    for yf_ticker in _B3_TICKERS:
        ticker = yf_ticker.replace(".SA", "")
        try:
            df = await svc.get_price_history(yf_ticker, period=period)
            closes = [float(r["fechamento"]) for r in df if r.get("fechamento")] if df else []
            sc = _compute_score(closes)

            all_scores.append(InvestmentScore(
                ticker=ticker,
                setor=_SECTOR_MAP.get(ticker),
                score=sc["score"],
                signal=_to_signal(sc["score"]),
                sub_scores=SubScores(
                    momentum=sc["momentum"],
                    trend=sc["trend"],
                    risk=sc["risk"],
                    rsi=sc["rsi"],
                ),
                total_return_1y=sc.get("total_return_1y"),
                volatility_annual=sc.get("volatility"),
                sharpe_approx=sc.get("sharpe"),
            ))
        except Exception as exc:
            logger.warning(f"Skipping {ticker} in insights: {exc}")

    all_scores.sort(key=lambda x: x.score, reverse=True)
    return InsightsResponse(
        period=period,
        assets_analyzed=len(all_scores),
        top_picks=all_scores[:top_n],
        all_scores=all_scores,
    )


@router.get("/score/{ticker}", response_model=InvestmentScore, summary="Single Ticker Score")
@cached(ttl=1800)
async def get_ticker_score(
    ticker: str,
    period: Annotated[str, Query()] = "1y",
) -> InvestmentScore:
    svc = YFinanceService()
    yf_ticker = f"{ticker.upper()}.SA"
    try:
        df = await svc.get_price_history(yf_ticker, period=period)
        closes = [float(r["fechamento"]) for r in df if r.get("fechamento")] if df else []
        sc = _compute_score(closes)
        return InvestmentScore(
            ticker=ticker.upper(),
            setor=_SECTOR_MAP.get(ticker.upper()),
            score=sc["score"],
            signal=_to_signal(sc["score"]),
            sub_scores=SubScores(
                momentum=sc["momentum"],
                trend=sc["trend"],
                risk=sc["risk"],
                rsi=sc["rsi"],
            ),
            total_return_1y=sc.get("total_return_1y"),
            volatility_annual=sc.get("volatility"),
            sharpe_approx=sc.get("sharpe"),
        )
    except Exception as exc:
        logger.error(f"Score computation failed for {ticker}: {exc}", exc_info=True)
        raise
