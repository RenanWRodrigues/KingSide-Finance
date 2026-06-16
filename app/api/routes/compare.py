from __future__ import annotations

import asyncio
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status

from app.core.cache import cache_get, cache_set
from app.core.logging import get_logger
from app.schemas.financial import (
    CompareMetrics,
    ComparePerformancePoint,
    ComparePerformanceSeries,
    CompareResponse,
)
from app.services.financial_data import BrapiService
from ml.quantitative_analysis.correlation import correlation_matrix
from ml.quantitative_analysis.indicators import technical_summary
from ml.quantitative_analysis.risk_metrics import compute_all

router = APIRouter(prefix="/compare", tags=["compare"])
logger = get_logger(__name__)

_COMPARE_TTL = 1800  # 30 min — histórico muda pouco intraday

_UNIVERSE_META: dict[str, tuple[str, str]] = {
    "PETR4": ("Petrobras", "Petróleo e Gás"),
    "VALE3": ("Vale", "Mineração"),
    "ITUB4": ("Itaú Unibanco", "Bancos"),
    "BBDC4": ("Bradesco", "Bancos"),
    "WEGE3": ("WEG", "Bens Industriais"),
    "ABEV3": ("Ambev", "Bebidas"),
    "BBSE3": ("BB Seguridade", "Seguros"),
    "TAEE11": ("Taesa", "Energia Elétrica"),
    "EGIE3": ("Engie Brasil", "Energia Elétrica"),
    "PRIO3": ("PetroRio", "Petróleo e Gás"),
    "BBAS3": ("Banco do Brasil", "Bancos"),
    "SANB11": ("Santander Brasil", "Bancos"),
    "ELET3": ("Eletrobras", "Energia Elétrica"),
    "SUZB3": ("Suzano", "Papel e Celulose"),
    "KLBN11": ("Klabin", "Papel e Celulose"),
    "MGLU3": ("Magazine Luiza", "Varejo"),
    "LREN3": ("Lojas Renner", "Varejo"),
    "ASAI3": ("Assaí Atacadista", "Varejo Alimentar"),
    "TOTS3": ("Totvs", "Tecnologia"),
    "CYRE3": ("Cyrela", "Construção Civil"),
    "RAIL3": ("Rumo", "Logística"),
    "RENT3": ("Localiza", "Locação de Veículos"),
    "SBSP3": ("Sabesp", "Saneamento"),
    "RADL3": ("RaiaDrogasil", "Saúde"),
    "HAPV3": ("Hapvida", "Saúde"),
    "VIVT3": ("Telefônica Brasil", "Telecomunicações"),
    "JBSS3": ("JBS", "Alimentos"),
    "EMBR3": ("Embraer", "Bens Industriais"),
    "CMIG4": ("CEMIG", "Energia Elétrica"),
    "CSAN3": ("Cosan", "Petróleo e Gás"),
}

_PERIOD_FALLBACKS: dict[str, list[str]] = {
    "1y": ["1y", "6mo", "3mo"],
    "6mo": ["6mo", "3mo"],
    "3mo": ["3mo", "1mo"],
    "1mo": ["1mo"],
}


def _parse_tickers(raw: str) -> list[str]:
    tickers = [t.strip().upper() for t in raw.split(",") if t.strip()]
    if len(tickers) < 2:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Informe pelo menos 2 tickers")
    if len(tickers) > 5:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Máximo de 5 tickers por comparação")
    return tickers


async def _fetch_history(ticker: str, period: str) -> list[dict]:
    """Fetch daily OHLCV from brapi with period fallbacks for free plan compatibility."""
    brapi = BrapiService()
    for p in _PERIOD_FALLBACKS.get(period, ["1y", "6mo", "3mo"]):
        try:
            records = await brapi.get_price_history(ticker, period=p)
            if records:
                return records
        except Exception as e:
            logger.warning(f"History {ticker} period={p}: {e}")
    return []


async def _build_compare_data(tickers: list[str], period: str) -> dict:
    cache_key = f"compare:{period}:{','.join(sorted(tickers))}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    # Fetch history concurrently — semaphore limits to 2 parallel brapi calls
    sem = asyncio.Semaphore(2)

    async def _fetch_one(ticker: str) -> tuple[str, list[dict]]:
        async with sem:
            try:
                data = await asyncio.wait_for(_fetch_history(ticker, period), timeout=20.0)
                await asyncio.sleep(0.2)
                return ticker, data
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning(f"History fetch failed for {ticker}: {e}")
                return ticker, []

    results = await asyncio.gather(*[_fetch_one(t) for t in tickers])
    histories: dict[str, list[dict]] = dict(results)

    prices_dict: dict[str, list[float]] = {
        t: [r["fechamento"] for r in records]
        for t, records in histories.items()
        if records
    }

    # Market proxy = equal-weighted average of all available price series (for beta/alpha)
    if len(prices_dict) >= 2:
        min_len = min(len(v) for v in prices_dict.values())
        mkt_avg: list[float] = []
        keys = list(prices_dict.keys())
        for i in range(min_len):
            avg = sum(prices_dict[k][-(min_len - i)] for k in keys) / len(keys)
            mkt_avg.append(avg)
    else:
        mkt_avg = []

    corr = correlation_matrix(prices_dict) if len(prices_dict) >= 2 else {}

    metrics_list = []
    perf_series = []

    for ticker in tickers:
        nome, setor = _UNIVERSE_META.get(ticker, (ticker, None))
        prices = prices_dict.get(ticker, [])
        records = histories.get(ticker, [])

        rm = compute_all(prices, mkt_avg or None) if prices else {}
        tech = technical_summary(prices) if prices else {}

        metrics_list.append({
            "ticker": ticker,
            "nome": nome,
            "setor": setor,
            "preco_atual": round(prices[-1], 2) if prices else None,
            "retorno_acumulado": rm.get("retorno_acumulado"),
            "cagr": rm.get("cagr"),
            "volatilidade_anual": rm.get("volatilidade_anual"),
            "sharpe": rm.get("sharpe"),
            "sortino": rm.get("sortino"),
            "max_drawdown": rm.get("max_drawdown"),
            "beta": rm.get("beta"),
            "alpha": rm.get("alpha"),
            "var_95": rm.get("var_95"),
            "rsi_14": tech.get("rsi_14"),
            "ma_20": tech.get("ma_20"),
            "ma_50": tech.get("ma_50"),
            "ma_200": tech.get("ma_200"),
        })

        if records and records[0]["fechamento"] > 0:
            base = records[0]["fechamento"]
            pontos = [
                {
                    "data": r["data"].isoformat() if hasattr(r["data"], "isoformat") else str(r["data"]),
                    "fechamento": r["fechamento"],
                    "normalizado": round(r["fechamento"] / base * 100, 2),
                }
                for r in records
            ]
        else:
            pontos = []

        perf_series.append({"ticker": ticker, "nome": nome, "setor": setor, "pontos": pontos})

    result = {
        "tickers": tickers,
        "periodo": period,
        "metrics": metrics_list,
        "correlacao": corr,
        "performance": perf_series,
    }

    await cache_set(cache_key, result, _COMPARE_TTL)
    return result


@router.get(
    "",
    response_model=CompareResponse,
    summary="Full comparison: performance, risk metrics and correlation",
)
async def compare_assets(
    tickers: str = Query(description="Comma-separated tickers, 2–5 (e.g. PETR4,VALE3,ITUB4)"),
    periodo: str = Query(default="1y", description="1mo, 3mo, 6mo, 1y"),
) -> CompareResponse:
    parsed = _parse_tickers(tickers)
    data = await _build_compare_data(parsed, periodo)
    return CompareResponse(
        tickers=data["tickers"],
        periodo=data["periodo"],
        metrics=[CompareMetrics(**m) for m in data["metrics"]],
        correlacao=data["correlacao"],
        performance=[
            ComparePerformanceSeries(
                ticker=s["ticker"],
                nome=s["nome"],
                setor=s.get("setor"),
                pontos=[ComparePerformancePoint(**p) for p in s["pontos"]],
            )
            for s in data["performance"]
        ],
    )


@router.get(
    "/performance",
    summary="Normalized historical performance series for charting",
)
async def compare_performance(
    tickers: str = Query(description="Comma-separated tickers"),
    periodo: str = Query(default="1y"),
) -> dict:
    parsed = _parse_tickers(tickers)
    data = await _build_compare_data(parsed, periodo)
    return {"tickers": data["tickers"], "periodo": data["periodo"], "series": data["performance"]}


@router.get(
    "/risk",
    summary="Risk metrics table: Sharpe, Sortino, Volatility, MaxDD, CAGR, Beta",
)
async def compare_risk(
    tickers: str = Query(description="Comma-separated tickers"),
    periodo: str = Query(default="1y"),
) -> dict:
    parsed = _parse_tickers(tickers)
    data = await _build_compare_data(parsed, periodo)
    return {"tickers": data["tickers"], "periodo": data["periodo"], "metrics": data["metrics"]}


@router.get(
    "/correlation",
    summary="Pearson correlation matrix on daily returns",
)
async def compare_correlation(
    tickers: str = Query(description="Comma-separated tickers"),
    periodo: str = Query(default="1y"),
    metodo: Literal["pearson", "spearman", "kendall"] = Query(default="pearson"),
) -> dict:
    parsed = _parse_tickers(tickers)
    data = await _build_compare_data(parsed, periodo)

    if metodo != "pearson":
        histories: dict[str, list[dict]] = {}
        for ticker in parsed:
            histories[ticker] = await _fetch_history(ticker, periodo)
            await asyncio.sleep(0.3)
        prices_dict = {t: [r["fechamento"] for r in v] for t, v in histories.items() if v}
        corr = correlation_matrix(prices_dict, method=metodo) if len(prices_dict) >= 2 else {}
    else:
        corr = data["correlacao"]

    return {"tickers": data["tickers"], "periodo": periodo, "metodo": metodo, "correlacao": corr}


@router.get(
    "/fundamentals",
    summary="Live fundamental data: market cap, dividend yield, 52w range",
)
async def compare_fundamentals(
    tickers: str = Query(description="Comma-separated tickers"),
) -> dict:
    import httpx

    from app.core.config import settings

    parsed = _parse_tickers(tickers)
    items = []
    for ticker in parsed:
        nome, setor = _UNIVERSE_META.get(ticker, (ticker, None))
        try:
            url = f"https://brapi.dev/api/quote/{ticker}"
            params = {"token": settings.BRAPI_TOKEN}
            async with httpx.AsyncClient(timeout=12) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
            results = resp.json().get("results", [])
            r = results[0] if results else {}
            items.append({
                "ticker": ticker,
                "nome": nome,
                "setor": setor,
                "preco_atual": r.get("regularMarketPrice"),
                "variacao_diaria_pct": r.get("regularMarketChangePercent"),
                "market_cap_bilhoes": round(float(r["marketCap"]) / 1e9, 2) if r.get("marketCap") else None,
                "dividend_yield": r.get("dividendYield"),
                "fiftyTwoWeekHigh": r.get("fiftyTwoWeekHigh"),
                "fiftyTwoWeekLow": r.get("fiftyTwoWeekLow"),
            })
        except Exception as e:
            logger.warning(f"Fundamentals {ticker}: {e}")
            items.append({"ticker": ticker, "nome": nome, "setor": setor})
        await asyncio.sleep(0.3)

    return {"tickers": parsed, "items": items}
