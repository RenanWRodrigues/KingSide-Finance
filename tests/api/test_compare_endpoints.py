"""API tests for /compare endpoints."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
def mock_brapi_history():
    """Synthetic 5-day price history for testing."""
    return [
        {"data": "2026-01-02", "fechamento": 40.0, "abertura": 39.5, "maxima": 40.5, "minima": 39.0, "volume": 1_000_000},
        {"data": "2026-01-03", "fechamento": 41.0, "abertura": 40.0, "maxima": 41.5, "minima": 39.8, "volume": 900_000},
        {"data": "2026-01-06", "fechamento": 42.0, "abertura": 41.0, "maxima": 42.5, "minima": 40.5, "volume": 1_100_000},
        {"data": "2026-01-07", "fechamento": 41.5, "abertura": 42.0, "maxima": 42.0, "minima": 41.0, "volume": 800_000},
        {"data": "2026-01-08", "fechamento": 43.0, "abertura": 41.5, "maxima": 43.5, "minima": 41.0, "volume": 1_200_000},
    ]


@pytest.fixture
def mock_brapi_history_long():
    """252-day synthetic price series (enough for Sharpe/Beta calculations)."""
    base = 100.0
    records = []
    from datetime import date, timedelta
    d = date(2025, 1, 2)
    for i in range(252):
        price = round(base * (1 + 0.0003 * i), 2)
        records.append({"data": d.isoformat(), "fechamento": price})
        d += timedelta(days=1)
    return records


class TestCompareEndpoints:
    @pytest.mark.asyncio
    @pytest.mark.api
    async def test_compare_requires_min_two_tickers(self, client):
        resp = await client.get("/api/v1/compare", params={"tickers": "PETR4"})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    @pytest.mark.api
    async def test_compare_rejects_more_than_five_tickers(self, client):
        resp = await client.get(
            "/api/v1/compare",
            params={"tickers": "PETR4,VALE3,ITUB4,BBDC4,WEGE3,ABEV3"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    @pytest.mark.api
    async def test_compare_success(self, client, mock_brapi_history):
        with (
            patch("app.api.routes.compare._fetch_history", new_callable=AsyncMock) as mock_hist,
            patch("app.core.cache.cache_get", new_callable=AsyncMock, return_value=None),
            patch("app.core.cache.cache_set", new_callable=AsyncMock, return_value=True),
        ):
            mock_hist.return_value = mock_brapi_history
            resp = await client.get(
                "/api/v1/compare",
                params={"tickers": "PETR4,VALE3", "periodo": "1mo"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "tickers" in data
        assert "metrics" in data
        assert "correlacao" in data
        assert "performance" in data
        assert len(data["metrics"]) == 2

    @pytest.mark.asyncio
    @pytest.mark.api
    async def test_compare_metrics_structure(self, client, mock_brapi_history):
        with (
            patch("app.api.routes.compare._fetch_history", new_callable=AsyncMock) as mock_hist,
            patch("app.core.cache.cache_get", new_callable=AsyncMock, return_value=None),
            patch("app.core.cache.cache_set", new_callable=AsyncMock, return_value=True),
        ):
            mock_hist.return_value = mock_brapi_history
            resp = await client.get(
                "/api/v1/compare",
                params={"tickers": "PETR4,VALE3", "periodo": "1mo"},
            )

        assert resp.status_code == 200
        metrics = resp.json()["metrics"]
        required_fields = {"ticker", "nome", "setor", "preco_atual", "retorno_acumulado"}
        for m in metrics:
            assert required_fields.issubset(m.keys())

    @pytest.mark.asyncio
    @pytest.mark.api
    async def test_compare_performance_series(self, client, mock_brapi_history):
        with (
            patch("app.api.routes.compare._fetch_history", new_callable=AsyncMock) as mock_hist,
            patch("app.core.cache.cache_get", new_callable=AsyncMock, return_value=None),
            patch("app.core.cache.cache_set", new_callable=AsyncMock, return_value=True),
        ):
            mock_hist.return_value = mock_brapi_history
            resp = await client.get(
                "/api/v1/compare",
                params={"tickers": "PETR4,VALE3", "periodo": "1mo"},
            )

        perf = resp.json()["performance"]
        for series in perf:
            assert "ticker" in series
            assert "pontos" in series
            if series["pontos"]:
                first_point = series["pontos"][0]
                assert first_point["normalizado"] == pytest.approx(100.0, abs=0.01)

    @pytest.mark.asyncio
    @pytest.mark.api
    async def test_compare_correlation_matrix(self, client, mock_brapi_history):
        with (
            patch("app.api.routes.compare._fetch_history", new_callable=AsyncMock) as mock_hist,
            patch("app.core.cache.cache_get", new_callable=AsyncMock, return_value=None),
            patch("app.core.cache.cache_set", new_callable=AsyncMock, return_value=True),
        ):
            mock_hist.return_value = mock_brapi_history
            resp = await client.get(
                "/api/v1/compare",
                params={"tickers": "PETR4,VALE3", "periodo": "1mo"},
            )

        corr = resp.json()["correlacao"]
        for ticker in ["PETR4", "VALE3"]:
            assert ticker in corr
            assert corr[ticker][ticker] == pytest.approx(1.0, abs=0.001)

    @pytest.mark.asyncio
    @pytest.mark.api
    async def test_compare_risk_endpoint(self, client, mock_brapi_history):
        with (
            patch("app.api.routes.compare._fetch_history", new_callable=AsyncMock) as mock_hist,
            patch("app.core.cache.cache_get", new_callable=AsyncMock, return_value=None),
            patch("app.core.cache.cache_set", new_callable=AsyncMock, return_value=True),
        ):
            mock_hist.return_value = mock_brapi_history
            resp = await client.get(
                "/api/v1/compare/risk",
                params={"tickers": "PETR4,VALE3", "periodo": "1mo"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "metrics" in data

    @pytest.mark.asyncio
    @pytest.mark.api
    async def test_compare_correlation_endpoint(self, client, mock_brapi_history):
        with (
            patch("app.api.routes.compare._fetch_history", new_callable=AsyncMock) as mock_hist,
            patch("app.core.cache.cache_get", new_callable=AsyncMock, return_value=None),
            patch("app.core.cache.cache_set", new_callable=AsyncMock, return_value=True),
        ):
            mock_hist.return_value = mock_brapi_history
            resp = await client.get(
                "/api/v1/compare/correlation",
                params={"tickers": "PETR4,VALE3", "periodo": "1mo"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "correlacao" in data
        assert "metodo" in data

    @pytest.mark.asyncio
    @pytest.mark.api
    async def test_compare_uses_cache(self, client, mock_brapi_history):
        cached_payload = {
            "tickers": ["PETR4", "VALE3"],
            "periodo": "1mo",
            "metrics": [
                {"ticker": "PETR4", "nome": "Petrobras", "setor": "Petróleo e Gás",
                 "preco_atual": 43.0, "retorno_acumulado": 7.5, "cagr": 7.5,
                 "volatilidade_anual": 25.0, "sharpe": 0.5, "sortino": 0.7,
                 "max_drawdown": -5.0, "beta": None, "alpha": None, "var_95": -1.5,
                 "rsi_14": 55.0, "ma_20": 41.5, "ma_50": None, "ma_200": None},
                {"ticker": "VALE3", "nome": "Vale", "setor": "Mineração",
                 "preco_atual": 65.0, "retorno_acumulado": 5.0, "cagr": 5.0,
                 "volatilidade_anual": 30.0, "sharpe": 0.3, "sortino": 0.4,
                 "max_drawdown": -8.0, "beta": None, "alpha": None, "var_95": -2.0,
                 "rsi_14": 48.0, "ma_20": 64.0, "ma_50": None, "ma_200": None},
            ],
            "correlacao": {"PETR4": {"PETR4": 1.0, "VALE3": 0.65}, "VALE3": {"PETR4": 0.65, "VALE3": 1.0}},
            "performance": [
                {"ticker": "PETR4", "nome": "Petrobras", "setor": "Petróleo e Gás",
                 "pontos": [{"data": "2026-01-02", "fechamento": 40.0, "normalizado": 100.0}]},
                {"ticker": "VALE3", "nome": "Vale", "setor": "Mineração",
                 "pontos": [{"data": "2026-01-02", "fechamento": 62.0, "normalizado": 100.0}]},
            ],
        }
        with patch("app.core.cache.cache_get", new_callable=AsyncMock, return_value=cached_payload):
            resp = await client.get(
                "/api/v1/compare",
                params={"tickers": "PETR4,VALE3", "periodo": "1mo"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["metrics"][0]["ticker"] == "PETR4"
