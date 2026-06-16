"""Tests for Prophet forecasting model."""

import pytest
import pandas as pd
import numpy as np
from datetime import date, timedelta


@pytest.fixture
def sample_prices() -> pd.DataFrame:
    dates = pd.bdate_range(start="2022-01-01", end="2024-12-31")
    np.random.seed(42)
    n = len(dates)
    trend = np.linspace(30, 50, n)
    noise = np.random.normal(0, 1, n)
    seasonality = 2 * np.sin(2 * np.pi * np.arange(n) / 252)
    prices = trend + noise + seasonality

    return pd.DataFrame({
        "date": dates,
        "close": prices,
        "open": prices * 0.99,
        "high": prices * 1.02,
        "low": prices * 0.98,
        "volume": np.random.randint(500_000, 5_000_000, n),
    })


class TestProphetForecaster:
    def test_prepare_dataframe(self, sample_prices):
        from ml.forecasting.prophet_model import ProphetForecaster

        forecaster = ProphetForecaster()
        df = forecaster._prepare_dataframe(sample_prices)

        assert "ds" in df.columns
        assert "y" in df.columns
        assert df["ds"].dtype == "datetime64[ns]"
        assert (df["y"] > 0).all()
        assert df["ds"].is_monotonic_increasing

    def test_prepare_dataframe_empty_raises(self):
        from ml.forecasting.prophet_model import ProphetForecaster

        forecaster = ProphetForecaster()
        with pytest.raises(Exception):
            forecaster.fit_predict("TEST", pd.DataFrame(), horizonte_dias=30, log_mlflow=False)

    def test_insufficient_data_raises(self):
        from ml.forecasting.prophet_model import ProphetForecaster

        forecaster = ProphetForecaster()
        tiny_df = pd.DataFrame({
            "date": pd.bdate_range("2026-01-01", periods=10),
            "close": [10.0] * 10,
        })
        with pytest.raises(ValueError, match="Insufficient data"):
            forecaster.fit_predict("TEST", tiny_df, horizonte_dias=30, log_mlflow=False)


class TestAnomalyDetector:
    def test_build_features(self, sample_prices):
        from ml.anomaly_detection.detector import MarketAnomalyDetector

        detector = MarketAnomalyDetector()
        df = sample_prices.set_index("date").rename(columns={"close": "close"})
        features = detector.build_features(df)

        expected_cols = ["ret_1d", "ret_5d", "vol_5d", "vol_21d", "volume_zscore"]
        for col in expected_cols:
            assert col in features.columns

    def test_fit_detect_returns_result(self, sample_prices):
        from ml.anomaly_detection.detector import MarketAnomalyDetector

        detector = MarketAnomalyDetector(contamination=0.05)
        df = sample_prices.set_index("date")
        result = detector.fit_detect("PETR4", df)

        assert result.ticker == "PETR4"
        assert result.total_points > 0
        assert 0 <= result.anomaly_rate <= 1
        assert result.anomaly_count == len(result.anomalies)
