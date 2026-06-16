"""Shared pytest fixtures for the Finance test suite."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient


# ── HTTP client ───────────────────────────────────────────────────────────────

@pytest.fixture
async def client():
    """ASGI test client shared across all API test modules."""
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


# ── Database / cache mocks ────────────────────────────────────────────────────

@pytest.fixture
def mock_db_conn():
    """Async context-manager mock for engine.connect()."""
    conn = MagicMock()
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=None)
    conn.execute = AsyncMock()
    return conn


@pytest.fixture
def mock_redis():
    """Redis async mock with ping() and common cache methods."""
    redis = AsyncMock()
    redis.ping = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    return redis


# ── Synthetic price data ──────────────────────────────────────────────────────

@pytest.fixture
def price_history_5d():
    """5-day synthetic OHLCV records (BRL format)."""
    return [
        {"data": "2026-05-01", "abertura": 38.0, "maxima": 39.0, "minima": 37.5,
         "fechamento": 38.5, "volume": 1_000_000, "variacao_dia_pct": 1.32},
        {"data": "2026-05-02", "abertura": 38.5, "maxima": 40.0, "minima": 38.0,
         "fechamento": 39.5, "volume": 1_200_000, "variacao_dia_pct": 2.60},
        {"data": "2026-05-05", "abertura": 39.5, "maxima": 41.0, "minima": 39.0,
         "fechamento": 40.0, "volume": 950_000, "variacao_dia_pct": 1.27},
        {"data": "2026-05-06", "abertura": 40.0, "maxima": 40.5, "minima": 39.0,
         "fechamento": 39.8, "volume": 800_000, "variacao_dia_pct": -0.50},
        {"data": "2026-05-07", "abertura": 39.8, "maxima": 41.5, "minima": 39.5,
         "fechamento": 41.0, "volume": 1_100_000, "variacao_dia_pct": 3.02},
    ]
