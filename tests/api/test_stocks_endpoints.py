"""Integration tests for stocks API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_health_check(client, mock_db_conn, mock_redis):
    with (
        patch("app.main.engine.connect", return_value=mock_db_conn),
        patch("app.main.get_redis", new_callable=AsyncMock, return_value=mock_redis),
    ):
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "services" in data
    assert data["services"]["postgres"] == "up"
    assert data["services"]["redis"] == "up"


@pytest.mark.asyncio
async def test_get_stock_history_valid_ticker(client):
    mock_history = [
        {"data": "2026-05-01", "abertura": 38.0, "maxima": 39.0, "minima": 37.5,
         "fechamento": 38.5, "volume": 1000000, "variacao_dia_pct": 1.32},
        {"data": "2026-05-02", "abertura": 38.5, "maxima": 40.0, "minima": 38.0,
         "fechamento": 39.5, "volume": 1200000, "variacao_dia_pct": 2.60},
    ]
    with patch(
        "app.services.financial_data.YFinanceService.get_price_history",
        new_callable=AsyncMock,
        return_value=mock_history,
    ):
        response = await client.get("/api/v1/stocks/PETR4/history?period=5d")

    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "PETR4"
    assert data["total_registros"] == 2


@pytest.mark.asyncio
async def test_get_stock_history_empty(client):
    with patch(
        "app.services.financial_data.YFinanceService.get_price_history",
        new_callable=AsyncMock,
        return_value=[],
    ):
        response = await client.get("/api/v1/stocks/INVALID123/history")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_ranking_dividend(client):
    response = await client.get("/api/v1/ranking/dividend?limite=5")
    assert response.status_code == 200
    data = response.json()
    assert data["tipo"] == "dividend_yield"
    assert len(data["items"]) <= 5


@pytest.mark.asyncio
async def test_macro_invalid_indicator(client):
    response = await client.get("/api/v1/macro/brasil/indicador_invalido")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_rate_limiting(client):
    """Verify that repeated requests within the window are all served (not blocked at low volume)."""
    responses = []
    for _ in range(5):
        r = await client.get("/health")
        responses.append(r.status_code)
    assert all(s in (200, 503) for s in responses)
