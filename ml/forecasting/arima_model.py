from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import mlflow
import numpy as np
import pandas as pd
from loguru import logger


@dataclass
class ARIMAConfig:
    auto_arima: bool = True
    p: int = 2
    d: int = 1
    q: int = 2
    seasonal: bool = True
    m: int = 5  # business week
    P: int = 1
    D: int = 1
    Q: int = 1
    information_criterion: str = "aic"
    max_p: int = 5
    max_q: int = 5


@dataclass
class ARIMAResult:
    ticker: str
    modelo: str = "arima"
    order: tuple[int, int, int] = (1, 1, 1)
    seasonal_order: tuple[int, int, int, int] = (0, 0, 0, 0)
    forecasts: list[dict[str, Any]] = field(default_factory=list)
    metricas: dict[str, float] = field(default_factory=dict)
    mlflow_run_id: str | None = None


class ARIMAForecaster:
    """
    SARIMA-based forecaster using pmdarima auto_arima for order selection.
    Suitable for stationary or trend-stationary financial series.
    """

    def __init__(self, config: ARIMAConfig | None = None) -> None:
        self.config = config or ARIMAConfig()

    def fit_predict(
        self,
        ticker: str,
        prices: pd.Series,
        horizonte_dias: int = 30,
        log_mlflow: bool = True,
    ) -> ARIMAResult:
        import pmdarima as pm
        from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error

        series = prices.dropna()
        if len(series) < 60:
            raise ValueError(f"Insufficient data for ARIMA on {ticker}")

        train_size = int(len(series) * 0.85)
        train, test = series[:train_size], series[train_size:]

        if self.config.auto_arima:
            model = pm.auto_arima(
                train,
                seasonal=self.config.seasonal,
                m=self.config.m,
                information_criterion=self.config.information_criterion,
                max_p=self.config.max_p,
                max_q=self.config.max_q,
                stepwise=True,
                suppress_warnings=True,
                error_action="ignore",
                n_jobs=-1,
            )
        else:
            model = pm.ARIMA(
                order=(self.config.p, self.config.d, self.config.q),
                seasonal_order=(self.config.P, self.config.D, self.config.Q, self.config.m),
            )
            model.fit(train)

        order = model.order
        seasonal_order = model.seasonal_order

        # Backtest
        n_test = len(test)
        backtest_pred, _ = model.predict(n_periods=n_test, return_conf_int=True)
        mae = mean_absolute_error(test.values, backtest_pred)
        mape = mean_absolute_percentage_error(test.values, backtest_pred)

        # Refit on full data
        model.update(test)
        forecast_values, conf_int = model.predict(n_periods=horizonte_dias, return_conf_int=True)

        last_date = series.index[-1] if hasattr(series.index, "__iter__") else pd.Timestamp.today()
        if not isinstance(last_date, pd.Timestamp):
            last_date = pd.Timestamp(str(last_date))

        forecasts = []
        for i, (pred, ci) in enumerate(zip(forecast_values, conf_int)):
            future_date = last_date + pd.offsets.BDay(i + 1)
            forecasts.append({
                "data_forecast": future_date.date(),
                "preco_previsto": round(float(pred), 6),
                "lower_bound": round(float(ci[0]), 6),
                "upper_bound": round(float(ci[1]), 6),
                "confianca": 0.95,
            })

        metricas = {
            "mae": round(mae, 4),
            "mape": round(mape, 4),
            "aic": round(model.aic(), 4),
        }

        run_id = None
        if log_mlflow:
            run_id = self._log_to_mlflow(ticker, order, seasonal_order, metricas, horizonte_dias)

        logger.info(
            f"ARIMA forecast for {ticker}: order={order}, seasonal={seasonal_order}, "
            f"MAE={mae:.4f}, MAPE={mape:.4f}"
        )
        return ARIMAResult(
            ticker=ticker,
            modelo="sarima",
            order=order,
            seasonal_order=seasonal_order,
            forecasts=forecasts,
            metricas=metricas,
            mlflow_run_id=run_id,
        )

    def _log_to_mlflow(
        self,
        ticker: str,
        order: tuple,
        seasonal_order: tuple,
        metricas: dict,
        horizonte_dias: int,
    ) -> str | None:
        try:
            with mlflow.start_run(run_name=f"arima_{ticker}") as run:
                mlflow.set_tag("model_type", "sarima")
                mlflow.set_tag("ticker", ticker)
                mlflow.log_params({
                    "p": order[0], "d": order[1], "q": order[2],
                    "P": seasonal_order[0], "D": seasonal_order[1],
                    "Q": seasonal_order[2], "m": seasonal_order[3],
                    "horizonte_dias": horizonte_dias,
                })
                mlflow.log_metrics(metricas)
                return run.info.run_id
        except Exception as e:
            logger.warning(f"MLflow logging failed: {e}")
            return None
