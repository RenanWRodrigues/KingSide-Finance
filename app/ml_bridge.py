"""Finance — Bridge between FastAPI routes and synchronous ML modules.

Wraps sync ML calls in asyncio.run_in_executor so FastAPI routes stay
non-blocking. Supports Prophet, ARIMA, and the proprietary InvestmentScorer.

Fallback chain: ML model → lightweight stub (price + linear drift) so the
API never returns 500 due to missing optional dependencies (prophet, pmdarima).
"""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pandas as pd
from loguru import logger

from app.schemas.financial import ForecastResponse

_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ml-bridge")

_VALID_MODELS = frozenset({"prophet", "arima"})


# ── Synchronous workers (run inside thread pool) ──────────────────────────────

def _prophet_worker(ticker: str, prices_df: pd.DataFrame, horizonte_dias: int) -> list[dict]:
    from ml.forecasting.prophet_model import ProphetConfig, ProphetForecaster

    forecaster = ProphetForecaster(ProphetConfig(seasonality_mode="multiplicative"))
    result = forecaster.fit_predict(
        ticker=ticker,
        prices=prices_df,
        horizonte_dias=horizonte_dias,
        log_mlflow=True,
    )
    return result.forecasts


def _arima_worker(ticker: str, prices_series: pd.Series, horizonte_dias: int) -> list[dict]:
    from ml.forecasting.arima_model import ARIMAForecaster

    forecaster = ARIMAForecaster()
    result = forecaster.fit_predict(
        ticker=ticker,
        prices=prices_series,
        horizonte_dias=horizonte_dias,
        log_mlflow=True,
    )
    return result.forecasts


def _scorer_worker(ticker: str, prices_df: pd.DataFrame) -> dict:
    from ml.investment_scoring.scorer import InvestmentScorer

    scorer = InvestmentScorer()
    prices = prices_df.set_index("data")["fechamento"]
    volumes = prices_df.set_index("data").get("volume")
    result = scorer.score(prices=prices, volumes=volumes)
    result.ticker = ticker
    return {
        "ticker": result.ticker,
        "score": result.score,
        "signal": result.signal,
        "total_return_1y": result.total_return_1y,
        "volatility_annual": result.volatility_annual,
        "sharpe_ratio": result.sharpe_ratio,
        "max_drawdown": result.max_drawdown,
        "components": {
            "momentum": result.components.momentum,
            "trend": result.components.trend,
            "risk": result.components.risk,
            "rsi": result.components.rsi,
            "volume": result.components.volume,
        },
    }


def _stub_forecasts(
    last_price: float,
    ticker: str,
    horizonte_dias: int,
    modelo: str,
) -> list[dict]:
    """Lightweight linear-drift fallback when ML dependencies are unavailable."""
    today = date.today()
    return [
        {
            "data_forecast": today + timedelta(days=i + 1),
            "preco_previsto": round(last_price * (1 + 0.0003 * (i + 1)), 6),
            "lower_bound": round(last_price * (1 - 0.05), 6),
            "upper_bound": round(last_price * (1 + 0.05), 6),
            "confianca": 0.50,
        }
        for i in range(horizonte_dias)
    ]


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _fetch_prices(ticker: str, period: str = "3y") -> pd.DataFrame:
    from app.services.financial_data import YFinanceService

    yf_service = YFinanceService()
    cotacoes = await yf_service.get_price_history(ticker, period=period)
    if not cotacoes:
        raise ValueError(f"No price data found for ticker '{ticker}'")
    return (
        pd.DataFrame(cotacoes)
        .assign(data=lambda df: pd.to_datetime(df["data"]))
        .sort_values("data")
        .reset_index(drop=True)
    )


def _to_forecast_responses(
    raw: list[dict],
    ticker: str,
    horizonte_dias: int,
    model_label: str,
) -> list[ForecastResponse]:
    now = datetime.now(timezone.utc)
    return [
        ForecastResponse(
            id=uuid4(),
            ticker=ticker,
            data_geracao=now,
            data_forecast=f["data_forecast"],
            modelo=model_label,
            horizonte_dias=horizonte_dias,
            preco_previsto=Decimal(str(round(float(f["preco_previsto"]), 6))),
            lower_bound=Decimal(str(round(float(f["lower_bound"]), 6))) if f.get("lower_bound") else None,
            upper_bound=Decimal(str(round(float(f["upper_bound"]), 6))) if f.get("upper_bound") else None,
            confianca=Decimal(str(f["confianca"])) if f.get("confianca") else None,
        )
        for f in raw
    ]


# ── Public async API ──────────────────────────────────────────────────────────

async def run_forecast(
    ticker: str,
    horizonte_dias: int = 30,
    modelo: str = "prophet",
) -> list[ForecastResponse]:
    """Fetch price data, run the ML model, return ForecastResponse objects.

    Falls back to a linear-drift stub if ML dependencies are not installed
    so the endpoint stays available in lightweight environments.

    Args:
        ticker: B3 ticker (e.g. "PETR4").
        horizonte_dias: Business days ahead to forecast (1–365).
        modelo: "prophet" or "arima".

    Raises:
        ValueError: Unknown model or no price data available.
    """
    if modelo not in _VALID_MODELS:
        raise ValueError(
            f"Unsupported model '{modelo}'. Valid options: {sorted(_VALID_MODELS)}"
        )

    prices_df = await _fetch_prices(ticker, period="3y")
    loop = asyncio.get_running_loop()

    try:
        if modelo == "prophet":
            raw: list[dict] = await asyncio.wait_for(
                loop.run_in_executor(_executor, _prophet_worker, ticker, prices_df, horizonte_dias),
                timeout=60.0,
            )
            model_label = "prophet"
        else:
            prices_series = prices_df.set_index("data")["fechamento"]
            raw = await asyncio.wait_for(
                loop.run_in_executor(_executor, _arima_worker, ticker, prices_series, horizonte_dias),
                timeout=60.0,
            )
            model_label = "sarima"
    except Exception as exc:
        logger.warning(
            f"ML model '{modelo}' failed for {ticker} ({type(exc).__name__}: {exc}) "
            "— falling back to linear-drift stub"
        )
        last_price = float(prices_df["fechamento"].iloc[-1])
        raw = _stub_forecasts(last_price, ticker, horizonte_dias, modelo)
        model_label = f"{modelo}-stub"

    logger.info(
        "Forecast complete",
        ticker=ticker,
        modelo=model_label,
        horizonte_dias=horizonte_dias,
        n_points=len(raw),
    )
    return _to_forecast_responses(raw, ticker, horizonte_dias, model_label)


async def run_forecast_async(
    ticker: str,
    horizonte_dias: int = 30,
    modelo: str = "prophet",
) -> None:
    """Fire-and-forget wrapper for FastAPI BackgroundTasks."""
    try:
        results = await run_forecast(ticker, horizonte_dias=horizonte_dias, modelo=modelo)
        logger.info(
            "Background forecast complete",
            ticker=ticker,
            modelo=modelo,
            n_points=len(results),
        )
    except Exception as e:
        logger.error(f"Background forecast failed for {ticker}: {e}", exc_info=True)
        raise


async def run_investment_score(ticker: str) -> dict:
    """Compute the proprietary multi-factor investment score (0–100) for a ticker."""
    prices_df = await _fetch_prices(ticker, period="1y")
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, _scorer_worker, ticker, prices_df)
