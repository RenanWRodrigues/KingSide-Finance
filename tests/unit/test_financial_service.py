"""Unit tests for financial data services."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

from app.services.financial_data import YFinanceService, BCBService


class TestYFinanceService:
    @pytest.fixture
    def service(self):
        return YFinanceService()

    @pytest.mark.asyncio
    async def test_get_ticker_info_success(self, service):
        mock_info = {
            "longName": "Petróleo Brasileiro SA",
            "sector": "Energy",
            "industry": "Oil & Gas",
            "currency": "BRL",
            "exchange": "B3",
            "country": "Brasil",
            "currentPrice": 38.50,
        }
        with patch("yfinance.Ticker") as mock_ticker:
            mock_ticker.return_value.info = mock_info
            result = await service.get_ticker_info.__wrapped__(service, "PETR4")

        assert result["ticker"] == "PETR4"
        assert result["nome"] == "Petróleo Brasileiro SA"
        assert result["setor"] == "Energy"

    @pytest.mark.asyncio
    async def test_get_ticker_info_failure(self, service):
        with patch("yfinance.Ticker") as mock_ticker:
            mock_ticker.return_value.info = {}
            mock_ticker.side_effect = Exception("Network error")
            with pytest.raises(RuntimeError, match="Could not fetch data"):
                await service.get_ticker_info.__wrapped__(service, "INVALID")

    @pytest.mark.asyncio
    async def test_get_price_history_success(self, service):
        import pandas as pd
        from datetime import date

        mock_df = pd.DataFrame({
            "date": pd.to_datetime(["2026-05-01", "2026-05-02"]),
            "open": [38.0, 38.5],
            "high": [39.0, 39.5],
            "low": [37.5, 38.0],
            "close": [38.5, 39.0],
            "volume": [1000000, 1200000],
        }).set_index("date")

        with patch("yfinance.Ticker") as mock_ticker:
            mock_ticker.return_value.history.return_value = mock_df
            result = await service.get_price_history.__wrapped__(service, "PETR4", period="5d")

        assert len(result) == 2
        assert result[0]["fechamento"] == 38.5
        assert result[1]["volume"] == 1200000

    @pytest.mark.asyncio
    async def test_get_price_history_empty(self, service):
        import pandas as pd

        with patch("yfinance.Ticker") as mock_ticker:
            mock_ticker.return_value.history.return_value = pd.DataFrame()
            result = await service.get_price_history.__wrapped__(service, "PETR4")

        assert result == []

    def test_safe_decimal_valid(self, service):
        assert service._safe_decimal(38.5) == Decimal("38.5")

    def test_safe_decimal_none(self, service):
        assert service._safe_decimal(None) is None

    def test_safe_decimal_nan(self, service):
        import math
        assert service._safe_decimal(float("nan")) is None


class TestBCBService:
    @pytest.fixture
    def service(self):
        return BCBService()

    def test_parse_date(self, service):
        from datetime import date
        result = service._parse_date("15/05/2026")
        assert result == date(2026, 5, 15)

    async def test_invalid_indicator(self, service):
        with pytest.raises(ValueError, match="not found"):
            await service.get_series.__wrapped__(service, "indicador_invalido")
