import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.advisory import router as advisory_router
from app.api.v1.attribution import router as attribution_router
from app.api.v1.auth import router as auth_router
from app.api.v1.cities import router as cities_router
from app.api.v1.compare import router as compare_router
from app.api.v1.enforcement import router as enforcement_router
from app.api.v1.forecasting import router as forecasting_router
from app.api.v1.health import router as health_router
from app.api.v1.ingestion import router as ingestion_router
from app.api.v1.public import router as public_router
from app.api.v1.reports import router as reports_router
from app.api.v1.users import router as users_router
from app.core.config import settings
from app.core.exceptions import VayuShieldError, vayushield_exception_handler
from app.core.logging import configure_logging, logger
from app.core.rate_limit import limiter
from app.db.seed import seed_admin


async def _refresh_city(city_id: str) -> None:
    """Poll readings + weather + run forecast + attribution for one city."""
    from app.core.database import AsyncSessionLocal
    from app.modules.attribution.service import compute_attribution
    from app.modules.forecasting.service import run_forecast
    from app.modules.ingestion.service import (
        poll_city_stations,
        poll_fire_hotspots,
        poll_satellite_aod,
        poll_traffic,
        poll_weather,
    )

    async with AsyncSessionLocal() as db:
        await poll_city_stations(db, city_id)
        await poll_weather(db, city_id)
        await poll_fire_hotspots(db, city_id)
        await poll_traffic(db, city_id)

    async with AsyncSessionLocal() as db:
        await run_forecast(db, city_id)

    async with AsyncSessionLocal() as db:
        await compute_attribution(db, city_id)

    async with AsyncSessionLocal() as db:
        from app.modules.cities.service import compute_vulnerability_scores
        await compute_vulnerability_scores(db, city_id)

    async with AsyncSessionLocal() as db:
        await poll_satellite_aod(db, city_id)

    # Discover emission sources once if none exist yet, then rank enforcement queue
    from sqlalchemy import text
    from app.modules.ingestion.service import (
        discover_and_import_emission_sources,
        _auto_rank_enforcement,
    )
    async with AsyncSessionLocal() as db:
        count_row = await db.execute(
            text("SELECT COUNT(*) FROM emission_sources WHERE city_id = :cid"),
            {"cid": city_id},
        )
        if (count_row.scalar() or 0) == 0:
            await discover_and_import_emission_sources(db, city_id)
            logger.info("Emission sources discovered", city_id=city_id)

    await _auto_rank_enforcement(city_id)

    logger.info("City refresh complete", city_id=city_id)


async def _startup_poll() -> None:
    """On startup: poll readings then immediately run forecast + attribution for every city."""
    try:
        from sqlalchemy import select

        from app.core.database import AsyncSessionLocal
        from app.modules.cities.models import City

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(City.id))
            city_ids = [row[0] for row in result.all()]

        for city_id in city_ids:
            try:
                await _refresh_city(city_id)
            except Exception as exc:
                logger.warning("City refresh failed", city_id=city_id, error=str(exc))
    except Exception as exc:
        logger.warning("Startup poll failed (non-fatal)", error=str(exc))


async def _background_poller() -> None:
    """Refresh all cities every 30 minutes so data never goes stale."""
    await asyncio.sleep(1800)  # wait 30 min after startup (startup already did a fresh run)
    while True:
        try:
            from sqlalchemy import select

            from app.core.database import AsyncSessionLocal
            from app.modules.cities.models import City

            async with AsyncSessionLocal() as db:
                result = await db.execute(select(City.id))
                city_ids = [row[0] for row in result.all()]

            for city_id in city_ids:
                try:
                    await _refresh_city(city_id)
                except Exception as exc:
                    logger.warning("Background refresh failed", city_id=city_id, error=str(exc))
        except Exception as exc:
            logger.warning("Background poller error", error=str(exc))
        await asyncio.sleep(1800)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("VayuShield AI starting", environment=settings.ENVIRONMENT)
    await seed_admin()
    asyncio.create_task(_startup_poll())
    asyncio.create_task(_background_poller())
    yield
    logger.info("VayuShield AI shutting down")


app = FastAPI(
    title="VayuShield AI",
    description="Urban Air Quality Intelligence Platform",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(VayuShieldError, vayushield_exception_handler)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception", exc_info=exc, path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "data": None,
            "meta": None,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": {},
            },
        },
    )


app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(
    compare_router, prefix="/api/v1"
)  # must be before cities_router (avoids /{city_id} conflict)
app.include_router(cities_router, prefix="/api/v1")
app.include_router(ingestion_router, prefix="/api/v1")
app.include_router(attribution_router, prefix="/api/v1")
app.include_router(forecasting_router, prefix="/api/v1")
app.include_router(enforcement_router, prefix="/api/v1")
app.include_router(advisory_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(public_router, prefix="/api/v1")
