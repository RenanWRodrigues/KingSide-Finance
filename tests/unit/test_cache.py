"""Unit tests for app/core/cache.py."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _async_gen(*keys: str):
    """Return a callable that produces a fresh async generator of *keys* each call."""
    async def _gen(**_kwargs):
        for k in keys:
            yield k
    return _gen


def _make_redis(scalar_result=None, scalars_result=None):
    """Build a minimal mocked aioredis.Redis."""
    r = AsyncMock()
    r.get = AsyncMock(return_value=json.dumps(scalar_result) if scalar_result is not None else None)
    r.setex = AsyncMock(return_value=True)
    r.delete = AsyncMock(return_value=1)
    r.scan_iter = _async_gen()  # empty by default
    return r


# ── cache_get ─────────────────────────────────────────────────────────────────

class TestCacheGet:
    async def test_hit_deserialises_json(self):
        from app.core.cache import cache_get

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=json.dumps({"ticker": "PETR4", "value": 42}))
        with patch("app.core.cache.get_redis", return_value=redis):
            result = await cache_get("some_key")

        assert result == {"ticker": "PETR4", "value": 42}

    async def test_miss_returns_none(self):
        from app.core.cache import cache_get

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        with patch("app.core.cache.get_redis", return_value=redis):
            result = await cache_get("missing_key")

        assert result is None

    async def test_redis_exception_returns_none(self):
        from app.core.cache import cache_get

        with patch("app.core.cache.get_redis", side_effect=Exception("Redis down")):
            result = await cache_get("key")

        assert result is None


# ── cache_set ─────────────────────────────────────────────────────────────────

class TestCacheSet:
    async def test_success_returns_true(self):
        from app.core.cache import cache_set

        redis = AsyncMock()
        redis.setex = AsyncMock(return_value=True)
        with patch("app.core.cache.get_redis", return_value=redis):
            ok = await cache_set("key", {"data": [1, 2, 3]}, ttl=120)

        assert ok is True
        redis.setex.assert_awaited_once()
        args = redis.setex.call_args.args
        assert args[0] == "key"
        assert args[1] == 120
        assert json.loads(args[2]) == {"data": [1, 2, 3]}

    async def test_exception_returns_false(self):
        from app.core.cache import cache_set

        with patch("app.core.cache.get_redis", side_effect=ConnectionError("unreachable")):
            ok = await cache_set("key", "value")

        assert ok is False


# ── cache_delete ──────────────────────────────────────────────────────────────

class TestCacheDelete:
    async def test_delete_calls_redis(self):
        from app.core.cache import cache_delete

        redis = AsyncMock()
        redis.delete = AsyncMock(return_value=1)
        with patch("app.core.cache.get_redis", return_value=redis):
            ok = await cache_delete("some_key")

        assert ok is True
        redis.delete.assert_awaited_once_with("some_key")

    async def test_exception_returns_false(self):
        from app.core.cache import cache_delete

        with patch("app.core.cache.get_redis", side_effect=Exception):
            ok = await cache_delete("key")

        assert ok is False


# ── cache_delete_pattern ──────────────────────────────────────────────────────

class TestCacheDeletePattern:
    async def test_uses_scan_iter_not_keys(self):
        """Verifies SCAN is used (non-blocking) instead of KEYS."""
        from app.core.cache import cache_delete_pattern

        deleted: list[str] = []
        redis = AsyncMock()
        redis.scan_iter = _async_gen("yf_history:PETR4:1", "yf_history:PETR4:2")
        redis.delete = AsyncMock(side_effect=lambda k: deleted.append(k))

        with patch("app.core.cache.get_redis", return_value=redis):
            count = await cache_delete_pattern("yf_history:PETR4:*")

        assert count == 2
        assert set(deleted) == {"yf_history:PETR4:1", "yf_history:PETR4:2"}

    async def test_empty_pattern_returns_zero(self):
        from app.core.cache import cache_delete_pattern

        redis = AsyncMock()
        redis.scan_iter = _async_gen()  # no matching keys
        redis.delete = AsyncMock()

        with patch("app.core.cache.get_redis", return_value=redis):
            count = await cache_delete_pattern("nonexistent:*")

        assert count == 0
        redis.delete.assert_not_awaited()

    async def test_exception_returns_zero(self):
        from app.core.cache import cache_delete_pattern

        with patch("app.core.cache.get_redis", side_effect=Exception("timeout")):
            count = await cache_delete_pattern("any:*")

        assert count == 0


# ── cache_invalidate_ticker ───────────────────────────────────────────────────

class TestCacheInvalidateTicker:
    async def test_covers_all_ticker_prefixes(self):
        from app.core.cache import cache_invalidate_ticker, _TICKER_CACHE_PREFIXES

        with patch(
            "app.core.cache.cache_delete_pattern",
            new_callable=AsyncMock,
            return_value=3,
        ) as mock_del:
            total = await cache_invalidate_ticker("VALE3")

        assert mock_del.await_count == len(_TICKER_CACHE_PREFIXES)
        assert total == 3 * len(_TICKER_CACHE_PREFIXES)
        patterns_called = [c.args[0] for c in mock_del.call_args_list]
        for pattern in patterns_called:
            assert "VALE3" in pattern
            assert pattern.endswith(":*")

    async def test_returns_zero_when_no_keys(self):
        from app.core.cache import cache_invalidate_ticker

        with patch("app.core.cache.cache_delete_pattern", new_callable=AsyncMock, return_value=0):
            total = await cache_invalidate_ticker("XPTO3")

        assert total == 0


class TestCacheInvalidateMacro:
    async def test_covers_bcb_and_fred_prefixes(self):
        from app.core.cache import cache_invalidate_macro, _MACRO_CACHE_PREFIXES

        with patch(
            "app.core.cache.cache_delete_pattern",
            new_callable=AsyncMock,
            return_value=2,
        ) as mock_del:
            total = await cache_invalidate_macro("selic")

        assert mock_del.await_count == len(_MACRO_CACHE_PREFIXES)
        for c in mock_del.call_args_list:
            assert "selic" in c.args[0]


# ── cached() decorator ────────────────────────────────────────────────────────

class TestCachedDecorator:
    async def test_returns_cached_value_on_hit(self):
        from app.core.cache import cached

        @cached(ttl=300, key_prefix="test")
        async def fetch(ticker: str) -> dict:
            raise AssertionError("should not be called on cache hit")

        with (
            patch("app.core.cache.cache_get", new_callable=AsyncMock, return_value={"hit": True}),
            patch("app.core.cache.cache_set", new_callable=AsyncMock),
        ):
            result = await fetch("PETR4")

        assert result == {"hit": True}

    async def test_calls_function_and_caches_on_miss(self):
        from app.core.cache import cached

        store: dict[str, object] = {}

        async def fake_get(key: str):
            return store.get(key)

        async def fake_set(key: str, value: object, ttl: int):
            store[key] = value
            return True

        @cached(ttl=300, key_prefix="compute")
        async def expensive(ticker: str) -> dict:
            return {"ticker": ticker, "computed": True}

        with (
            patch("app.core.cache.cache_get", side_effect=fake_get),
            patch("app.core.cache.cache_set", side_effect=fake_set),
        ):
            result = await expensive("ITUB4")

        assert result == {"ticker": "ITUB4", "computed": True}
        assert len(store) == 1

    async def test_structured_key_contains_prefix_and_first_arg(self):
        """Key must be {prefix}:{first_arg}:{hash} for pattern invalidation to work."""
        from app.core.cache import cached

        captured: list[str] = []

        async def spy_get(key: str):
            captured.append(key)
            return None

        @cached(ttl=60, key_prefix="yf_history")
        async def fetch(ticker: str, period: str = "1y") -> list:
            return []

        with (
            patch("app.core.cache.cache_get", side_effect=spy_get),
            patch("app.core.cache.cache_set", new_callable=AsyncMock),
        ):
            await fetch("BBDC4", period="5y")

        assert len(captured) == 1
        key = captured[0]
        assert key.startswith("yf_history:")
        assert "BBDC4" in key

    async def test_different_first_args_produce_different_keys(self):
        from app.core.cache import cached

        keys_seen: list[str] = []

        async def spy_get(key: str):
            keys_seen.append(key)
            return None

        @cached(ttl=60, key_prefix="yf_history")
        async def fetch(ticker: str) -> list:
            return []

        with (
            patch("app.core.cache.cache_get", side_effect=spy_get),
            patch("app.core.cache.cache_set", new_callable=AsyncMock),
        ):
            await fetch("PETR4")
            await fetch("VALE3")

        assert len(keys_seen) == 2
        assert keys_seen[0] != keys_seen[1]
        assert "PETR4" in keys_seen[0]
        assert "VALE3" in keys_seen[1]

    async def test_skip_empty_list_not_cached(self):
        from app.core.cache import cached

        @cached(ttl=300, key_prefix="t", skip_empty=True)
        async def fetch(x: str) -> list:
            return []

        with (
            patch("app.core.cache.cache_get", new_callable=AsyncMock, return_value=None),
            patch("app.core.cache.cache_set", new_callable=AsyncMock) as mock_set,
        ):
            result = await fetch("x")

        assert result == []
        mock_set.assert_not_awaited()

    async def test_empty_dict_not_cached_when_skip_empty(self):
        from app.core.cache import cached

        @cached(ttl=300, key_prefix="t", skip_empty=True)
        async def fetch(x: str) -> dict:
            return {}

        with (
            patch("app.core.cache.cache_get", new_callable=AsyncMock, return_value=None),
            patch("app.core.cache.cache_set", new_callable=AsyncMock) as mock_set,
        ):
            result = await fetch("x")

        assert result == {}
        mock_set.assert_not_awaited()
