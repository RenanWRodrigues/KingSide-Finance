from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import mlflow
import pandas as pd
from loguru import logger


@dataclass
class ProphetConfig:
    changepoint_prior_scale: float = 0.05
    seasonality_prior_scale: float = 10.0
    seasonality_mode: str = "multiplicative"
    yearly_seasonality: bool = True
    weekly_seasonality: bool = True
    daily_seasonality: bool = False
    interval_width: float = 0.95
    n_changepoints: int = 25


@dataclass
class ForecastResult:
    ticker: str
    modelo: str = "prophet"
    horizonte_dias: int = 30
    forecasts: list[dict[str, Any]] = field(default_factory=list)
    metricas: dict[str, float] = field(default_factory=dict)
    mlflow_run_id: str | None = None


class ProphetForecaster:
    """
    Prophet-based price forecasting with MLflow experiment tracking.
    Implements additive/multiplicative seasonality for financial time series.
    """

    def __init__(self, config: ProphetConfig | None = None) -> None:
        self.config = config or ProphetConfig()

    def fit_predict(
        self,
        ticker: str,
        prices: pd.DataFrame,
        horizonte_dias: int = 30,
        log_mlflow: bool = True,
    ) -> ForecastResult:
        from prophet import Prophet
        from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error

        df = self._prepare_dataframe(prices)
        if len(df) < 30:
            raise ValueError(f"Insufficient data for {ticker}: need at least 30 points")

        train_size = int(len(df) * 0.85)
        train, test = df[:train_size], df[train_size:]

        model = Prophet(
            changepoint_prior_scale=self.config.changepoint_prior_scale,
            seasonality_prior_scale=self.config.seasonality_prior_scale,
            seasonality_mode=self.config.seasonality_mode,
            yearly_seasonality=self.config.yearly_seasonality,
            weekly_seasonality=self.config.weekly_seasonality,
            daily_seasonality=self.config.daily_seasonality,
            interval_width=self.config.interval_width,
            n_changepoints=self.config.n_changepoints,
        )
        model.add_country_holidays(country_name="BR")
        model.fit(train)

        # Backtest metrics
        test_forecast = model.predict(test[["ds"]])
        mae = mean_absolute_error(test["y"], test_forecast["yhat"])
        mape = mean_absolute_percentage_error(test["y"], test_forecast["yhat"])
        metricas = {"mae": round(mae, 4), "mape": round(mape, 4)}

        # Future forecast
        future = model.make_future_dataframe(periods=horizonte_dias, freq="B")
        forecast_df = model.predict(future)
        future_only = forecast_df[forecast_df["ds"] > df["ds"].max()]

        forecasts = [
            {
                "data_forecast": row["ds"].date(),
                "preco_previsto": round(float(row["yhat"]), 6),
                "lower_bound": round(float(row["yhat_lower"]), 6),
                "upper_bound": round(float(row["yhat_upper"]), 6),
                "confianca": self.config.interval_width,
            }
            for _, row in future_only.iterrows()
            if row["yhat"] > 0
        ]

        run_id = None
        if log_mlflow:
            run_id = self._log_to_mlflow(ticker, metricas, horizonte_dias)

        logger.info(f"Prophet forecast for {ticker}: {len(forecasts)} points, MAE={mae:.4f}")
        return ForecastResult(
            ticker=ticker,
            modelo="prophet",
            horizonte_dias=horizonte_dias,
            forecasts=forecasts,
            metricas=metricas,
            mlflow_run_id=run_id,
        )

    def _prepare_dataframe(self, prices: pd.DataFrame) -> pd.DataFrame:
        df = prices.copy()
        if "date" in df.columns:
            df = df.rename(columns={"date": "ds", "close": "y"})
        elif "data" in df.columns:
            df = df.rename(columns={"data": "ds", "fechamento": "y"})
        df["ds"] = pd.to_datetime(df["ds"])
        df = df[["ds", "y"]].dropna().sort_values("ds").reset_index(drop=True)
        return df

    def _log_to_mlflow(self, ticker: str, metricas: dict, horizonte_dias: int) -> str | None:
        try:
            with mlflow.start_run(run_name=f"prophet_{ticker}") as run:
                mlflow.set_tag("model_type", "prophet")
                mlflow.set_tag("ticker", ticker)
                mlflow.log_params({
                    "changepoint_prior_scale": self.config.changepoint_prior_scale,
                    "seasonality_mode": self.config.seasonality_mode,
                    "horizonte_dias": horizonte_dias,
                })
                mlflow.log_metrics(metricas)
                return run.info.run_id
        except Exception as e:
            logger.warning(f"MLflow logging failed: {e}")
            return None
