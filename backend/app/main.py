import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db
from app.redis_client import init_redis, close_redis
from app.tasks.scheduler import register_medazone_jobs, scheduler

# ── Routers ───────────────────────────────────────────────────────────────────
from app.routers import auth, fields, slots, bookings, subscriptions
from app.routers import reviews, notifications, payments, admin
from app.websockets.slots_ws import router as ws_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 MedaZone API starting up…")

    # 1. Database — ensure PostGIS extensions exist
    await init_db()

    # 2. Redis — open connection pool
    await init_redis()

    logger.info("✅ Database and Redis ready")

    # 3. Background jobs
    register_medazone_jobs()
    scheduler.start()
    logger.info("✅ APScheduler started")

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("🛑 MedaZone API shutting down…")
    scheduler.shutdown(wait=False)
    await close_redis()


# ── App instance ──────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "MedaZone — real-time football field discovery, slot booking, "
        "and subscription management for Addis Ababa."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Origins are read from BACKEND_CORS_ORIGINS (comma-separated) in the root .env
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── REST routers (all prefixed /api/v1) ───────────────────────────────────────
app.include_router(auth.router,          prefix="/api/v1")
app.include_router(fields.router,        prefix="/api/v1")
app.include_router(slots.router,         prefix="/api/v1")
app.include_router(bookings.router,      prefix="/api/v1")
app.include_router(subscriptions.router, prefix="/api/v1")
app.include_router(reviews.router,       prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(payments.router,      prefix="/api/v1")
app.include_router(admin.router,         prefix="/api/v1")

# ── WebSocket routers (under /ws/) ────────────────────────────────────────────
app.include_router(ws_router)   # /ws/fields/{field_id}


# ── Utility routes ────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"])
async def health_check():
    return JSONResponse(
        content={
            "status": "ok",
            "version": settings.APP_VERSION,
            "app": settings.APP_NAME,
        }
    )


@app.get("/", tags=["Health"])
async def root():
    return {"message": "MedaZone API", "docs": "/docs"}
