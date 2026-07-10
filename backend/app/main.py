from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.advisory import router as advisory_router
from app.api.v1.attribution import router as attribution_router
from app.api.v1.auth import router as auth_router
from app.api.v1.cities import router as cities_router
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
from app.db.seed import seed_admin


async def _startup_poll() -> None:
    """Trigger one ingestion cycle for every city so the dashboard is never empty."""
    try:
        from sqlalchemy import select

        from app.core.database import AsyncSessionLocal
        from app.modules.cities.models import City
        from app.modules.ingestion.service import (
            poll_city_stations,
            poll_fire_hotspots,
            poll_weather,
        )

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(City.id))
            city_ids = [row[0] for row in result.all()]

        for city_id in city_ids:
            async with AsyncSessionLocal() as db:
                await poll_city_stations(db, city_id)
                await poll_weather(db, city_id)
                await poll_fire_hotspots(db, city_id)
            logger.info("Startup poll complete", city_id=city_id)
    except Exception as exc:
        logger.warning("Startup poll failed (non-fatal)", error=str(exc))


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("VayuShield AI starting", environment=settings.ENVIRONMENT)
    await seed_admin()
    await _startup_poll()
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
app.include_router(cities_router, prefix="/api/v1")
app.include_router(ingestion_router, prefix="/api/v1")
app.include_router(attribution_router, prefix="/api/v1")
app.include_router(forecasting_router, prefix="/api/v1")
app.include_router(enforcement_router, prefix="/api/v1")
app.include_router(advisory_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(public_router, prefix="/api/v1")
