from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings
from app.models.audit import AuditEntry
from app.models.bidder import Bidder, BidderProfile
from app.models.tender import EvaluationSchema, Tender
from app.models.verdict import VerdictRecord

DOCUMENT_MODELS = [Tender, EvaluationSchema, Bidder, BidderProfile, VerdictRecord, AuditEntry]


async def init_db():
    client = AsyncIOMotorClient(settings.mongodb_url)
    await init_beanie(
        database=client.get_default_database("tenderproof"),
        document_models=DOCUMENT_MODELS,
    )


# Alias used inside synchronous Celery tasks via asyncio.run() — each task run
# creates a fresh event loop, so it needs its own Motor client.
init_db_sync = init_db
