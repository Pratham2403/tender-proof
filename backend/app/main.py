import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db
from app.routers import bidders, jobs, review, tenders
from app.ws.job_progress import JobProgressManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="TenderProof API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def limit_upload_size(request: Request, call_next):
    # Reject oversized uploads before reading the body (LLD §12: 50MB cap)
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.max_upload_mb * 1024 * 1024:
        return JSONResponse(
            status_code=413,
            content={"detail": f"Upload exceeds {settings.max_upload_mb}MB limit"},
        )
    return await call_next(request)


app.include_router(tenders.router)
app.include_router(bidders.router)
app.include_router(review.router)
app.include_router(jobs.router)

ws_manager = JobProgressManager()


@app.websocket("/ws/jobs/{job_id}")
async def job_ws(websocket: WebSocket, job_id: str):
    await ws_manager.stream(websocket, job_id)


@app.get("/api/health")
async def health():
    from app.models.tender import Tender

    mongo_ok = redis_ok = False
    try:
        await Tender.get_motor_collection().database.command("ping")
        mongo_ok = True
    except Exception:
        pass
    try:
        import redis as redis_lib
        r = redis_lib.from_url(settings.redis_url, socket_connect_timeout=2)
        redis_ok = bool(r.ping())
        r.close()
    except Exception:
        pass

    return {
        "status": "ok" if (mongo_ok and redis_ok) else "degraded",
        "mongo": mongo_ok,
        "redis": redis_ok,
    }
