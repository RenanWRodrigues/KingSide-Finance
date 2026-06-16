from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.middleware.rate_limit import RateLimitMiddleware
from app.core.config import settings
from app.core.logging import configure_logging, get_logger


configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Application starting",
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        env=settings.APP_ENV,
    )
    await _init_db()
    yield
    logger.info("Application shutting down", app=settings.APP_NAME)
    from app.core.cache import get_redis
    try:
        redis = await get_redis()
        await redis.aclose()
    except Exception:
        pass


async def _init_db() -> None:
    from app.core.database import engine, Base
    import app.models.financial  # noqa: F401 — registers models with Base.metadata

    try:
        async with engine.begin() as conn:
            for schema in ("raw", "staging", "intermediate", "marts", "analytics", "monitoring"):
                await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schemas and tables ready")
    except Exception as e:
        if "already exists" in str(e):
            logger.info("Database schemas already exist", detail="skipping creation")
        else:
            logger.warning(
                "Database init deferred — will retry on first request",
                reason=str(e),
            )


def create_app() -> FastAPI:
    app = FastAPI(
        title="Finance API",
        description=(
            "Enterprise Financial Analytics & Machine Learning Platform. "
            "Real-time market data, forecasting, and portfolio analytics."
        ),
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── Middleware ────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        RateLimitMiddleware,
        requests=settings.RATE_LIMIT_REQUESTS,
        window=settings.RATE_LIMIT_WINDOW,
    )

    # ── Routes ────────────────────────────────────────────────
    from app.api.routes import auth, compare, forecast, heatmap, insights, macro, ranking, sentiment, stocks

    prefix = settings.API_V1_PREFIX
    app.include_router(auth.router, prefix=prefix)
    app.include_router(stocks.router, prefix=prefix)
    app.include_router(forecast.router, prefix=prefix)
    app.include_router(ranking.router, prefix=prefix)
    app.include_router(compare.router, prefix=prefix)
    app.include_router(macro.router, prefix=prefix)
    app.include_router(sentiment.router, prefix=prefix)
    app.include_router(insights.router, prefix=prefix)
    app.include_router(heatmap.router, prefix=prefix)

    # ── Health ────────────────────────────────────────────────
    @app.get("/health", tags=["system"], summary="Health check")
    async def health() -> JSONResponse:
        """Check liveness and dependency readiness.

        Returns HTTP 200 when all dependencies are reachable, HTTP 503 when
        any is down. Docker, Kubernetes, and load balancers use the status
        code to decide whether to route traffic to this instance.
        """
        from app.core.database import engine
        from app.core.cache import get_redis

        services: dict[str, str] = {}

        # ── PostgreSQL ─────────────────────────────────────────
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            services["postgres"] = "up"
        except Exception as exc:
            services["postgres"] = f"down ({type(exc).__name__})"
            logger.warning("Health check: postgres unavailable", error=str(exc))

        # ── Redis ──────────────────────────────────────────────
        try:
            redis = await get_redis()
            await redis.ping()
            services["redis"] = "up"
        except Exception as exc:
            services["redis"] = f"down ({type(exc).__name__})"
            logger.warning("Health check: redis unavailable", error=str(exc))

        all_up = all(v == "up" for v in services.values())
        body = {
            "status": "healthy" if all_up else "degraded",
            "version": settings.APP_VERSION,
            "environment": settings.APP_ENV,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": services,
        }
        return JSONResponse(content=body, status_code=200 if all_up else 503)

    @app.get("/", tags=["system"], include_in_schema=False)
    async def root() -> dict:
        return {
            "service": "Finance API",
            "version": settings.APP_VERSION,
            "docs": "/docs",
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD,
        workers=1 if settings.API_RELOAD else settings.API_WORKERS,
        log_level=settings.LOG_LEVEL.lower(),
    )
