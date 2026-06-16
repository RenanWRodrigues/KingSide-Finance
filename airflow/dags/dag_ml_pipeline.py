

"""
Finance — Weekly ML Training & Forecasting Pipeline

Schedule: Every Sunday at 02:00 UTC
Tasks: Feature engineering → Model training → Forecast generation → Anomaly detection
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup


DEFAULT_ARGS = {
    "owner": "finance-ml-eng",
    "depends_on_past": False,
    "start_date": datetime(2024, 1, 1),
    "email_on_failure": True,
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
}

TICKERS = ["PETR4", "VALE3", "ITUB4", "BBDC4", "ABEV3", "WEGE3"]

# /opt/airflow is the standard Airflow Docker working directory;
# the project is mounted there so ML modules are importable.
_PROJECT_ROOT = "/opt/airflow"


def _ensure_project_on_path() -> None:
    import sys
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)


def _fetch_prices_df(ticker: str, period: str):
    import yfinance as yf
    import pandas as pd

    t = yf.Ticker(f"{ticker}.SA")
    df = t.history(period=period, auto_adjust=True).reset_index()
    df.columns = [c.lower() for c in df.columns]
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


def train_prophet_forecast(ticker: str, **context) -> None:
    _ensure_project_on_path()
    from ml.forecasting.prophet_model import ProphetForecaster, ProphetConfig

    df = _fetch_prices_df(ticker, period="3y")
    if df.empty:
        raise ValueError(f"No price data returned for {ticker}")

    forecaster = ProphetForecaster(ProphetConfig(seasonality_mode="multiplicative"))
    result = forecaster.fit_predict(
        ticker=ticker,
        prices=df,
        horizonte_dias=30,
        log_mlflow=True,
    )
    print(f"[{ticker}] Prophet: {len(result.forecasts)} forecasts, metrics={result.metricas}")


def train_arima_forecast(ticker: str, **context) -> None:
    _ensure_project_on_path()
    from ml.forecasting.arima_model import ARIMAForecaster

    df = _fetch_prices_df(ticker, period="3y")
    if df.empty:
        raise ValueError(f"No price data returned for {ticker}")

    prices_series = df.set_index("date")["close"]
    forecaster = ARIMAForecaster()
    result = forecaster.fit_predict(
        ticker=ticker,
        prices=prices_series,
        horizonte_dias=30,
        log_mlflow=True,
    )
    print(f"[{ticker}] ARIMA: {len(result.forecasts)} forecasts, metrics={result.metricas}")


def detect_anomalies(ticker: str, **context) -> None:
    _ensure_project_on_path()
    from ml.anomaly_detection.detector import MarketAnomalyDetector

    df = _fetch_prices_df(ticker, period="2y")
    if df.empty:
        raise ValueError(f"No price data returned for {ticker}")

    detector = MarketAnomalyDetector(contamination=0.02)
    result = detector.fit_detect(ticker=ticker, df=df)
    print(f"[{ticker}] Anomalies: {result.anomaly_count}/{result.total_points}")


def compute_investment_score(ticker: str, **context) -> None:
    _ensure_project_on_path()
    from ml.investment_scoring.scorer import InvestmentScorer

    df = _fetch_prices_df(ticker, period="1y")
    if df.empty:
        raise ValueError(f"No price data returned for {ticker}")

    prices = df.set_index("date")["close"]
    volumes = df.set_index("date").get("volume")
    scorer = InvestmentScorer()
    result = scorer.score(prices=prices, volumes=volumes)
    result.ticker = ticker
    print(f"[{ticker}] Score={result.score:.1f} signal={result.signal}")


with DAG(
    dag_id="finance_ml_pipeline",
    description="Weekly ML training, forecasting and anomaly detection",
    default_args=DEFAULT_ARGS,
    schedule_interval="0 2 * * 0",
    catchup=False,
    max_active_runs=1,
    tags=["finance", "ml", "weekly", "forecasting"],
    doc_md=__doc__,
) as dag:

    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end")

    with TaskGroup("forecasting") as fg:
        for _ticker in TICKERS:
            PythonOperator(
                task_id=f"prophet_{_ticker}",
                python_callable=train_prophet_forecast,
                op_kwargs={"ticker": _ticker},
            )

    with TaskGroup("arima_forecasting") as afg:
        for _ticker in TICKERS:
            PythonOperator(
                task_id=f"arima_{_ticker}",
                python_callable=train_arima_forecast,
                op_kwargs={"ticker": _ticker},
            )

    with TaskGroup("anomaly_detection") as ag:
        for _ticker in TICKERS:
            PythonOperator(
                task_id=f"anomaly_{_ticker}",
                python_callable=detect_anomalies,
                op_kwargs={"ticker": _ticker},
            )

    with TaskGroup("investment_scoring") as sg:
        for _ticker in TICKERS:
            PythonOperator(
                task_id=f"score_{_ticker}",
                python_callable=compute_investment_score,
                op_kwargs={"ticker": _ticker},
            )

    start >> fg >> afg >> ag >> sg >> end
