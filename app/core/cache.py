import json
from collections.abc import Callable
from functools import wraps
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings
from app.core.logging import get_logger


logger = get_logger(__name__)

_redis_client: aioredis.Redis | None = None

# Cache key prefixes used by YFinanceService — must stay in sync with @cached decorators.
_TICKER_CACHE_PREFIXES: tuple[str, ...] = (
    "yf_ticker_info",
    "yf_history",
    "yf_dividends",
    "yf_financials",
    "yf_quarterly_financials",
    "yf_balance_sheet",
    "yf_valuation",
    "brapi_history",
)

_MACRO_CACHE_PREFIXES: tuple[str, ...] = (
    "bcb_series",
    "fred_series",
)


async def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
    return _redis_client


async def cache_get(key: str) -> Any | None:
    try:
        redis = await get_redis()
        value = await redis.get(key)
        if value:
            return json.loads(value)
        return None
    except Exception as e:
        logger.warning(f"Cache GET failed for key '{key}': {e}")
        return None


async def cache_set(key: str, value: Any, ttl: int = 300) -> bool:
    try:
        redis = await get_redis()
        await redis.setex(key, ttl, json.dumps(value, default=str))
        return True
    except Exception as e:
        logger.warning(f"Cache SET failed for key '{key}': {e}")
        return False


async def cache_delete(key: str) -> bool:
    try:
        redis = await get_redis()
        await redis.delete(key)
        return True
    except Exception as e:
        logger.warning(f"Cache DELETE failed for key '{key}': {e}")
        return False


async def cache_delete_pattern(pattern: str) -> int:
    """Delete all keys matching *pattern* using cursor-based SCAN (non-blocking).

    Uses SCAN instead of KEYS so it never blocks the Redis server on large key spaces.
    """
    try:
        redis = await get_redis()
        count = 0
        async for key in redis.scan_iter(match=pattern, count=100):
            await redis.delete(key)
            count += 1
        return count
    except Exception as e:
        logger.warning(f"Cache DELETE PATTERN failed for '{pattern}': {e}")
        return 0


async def cache_invalidate_ticker(ticker: str) -> int:
    """Invalidate all cached responses that depend on *ticker*.

    Called after a successful price/dividend/financial upsert so subsequent
    API requests reflect the new data without waiting for TTL expiry.
    """
    total = 0
    for prefix in _TICKER_CACHE_PREFIXES:
        total += await cache_delete_pattern(f"{prefix}:{ticker}:*")
    if total:
        logger.info(f"Cache invalidated for ticker '{ticker}': {total} keys removed")
    return total


async def cache_invalidate_macro(indicator: str) -> int:
    """Invalidate all cached macro series responses for *indicator*."""
    total = 0
    for prefix in _MACRO_CACHE_PREFIXES:
        total += await cache_delete_pattern(f"{prefix}:{indicator}:*")
    if total:
        logger.info(f"Cache invalidated for macro indicator '{indicator}': {total} keys removed")
    return total


def cached(ttl: int = 300, key_prefix: str = "", skip_empty: bool = True):
    """Async cache decorator backed by Redis.

    When *key_prefix* is set the key is structured as
    ``{prefix}:{first_arg}:{hash_of_remaining_args}`` so callers can
    invalidate all entries for a specific ticker/indicator with
    ``cache_delete_pattern("{prefix}:{ticker}:*")``.

    Without *key_prefix* the key falls back to
    ``{func_name}:{hash_of_all_args}`` (route-handler style).
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Strip `self` so all instances of the same class share cache entries.
            key_args = args[1:] if args and hasattr(args[0], "__class__") else args

            if key_prefix and key_args:
                # Structured key: prefix + first arg (ticker/indicator) + hash of rest.
                first = str(key_args[0])
                rest_hash = hash(str(key_args[1:]) + str(sorted(kwargs.items())))
                cache_key = f"{key_prefix}:{first}:{rest_hash}"
            else:
                cache_key = f"{key_prefix or func.__name__}:{hash(str(key_args) + str(sorted(kwargs.items())))}"

            cached_value = await cache_get(cache_key)
            if cached_value is not None:
                return cached_value

            result = await func(*args, **kwargs)

            if skip_empty and isinstance(result, (list, dict)) and not result:
                return result

            await cache_set(cache_key, result, ttl)
            return result

        return wrapper

    return decorator
