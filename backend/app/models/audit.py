import hashlib
import json
from datetime import datetime
from enum import Enum

from beanie import Document
from pydantic import Field
from pymongo import ASCENDING, IndexModel


class AuditEventType(str, Enum):
    SCHEMA_COMPILED = "SCHEMA_COMPILED"
    SCHEMA_APPROVED = "SCHEMA_APPROVED"
    EXTRACTION_COMPLETE = "EXTRACTION_COMPLETE"
    VERDICT_PRODUCED = "VERDICT_PRODUCED"
    OFFICER_OVERRIDE = "OFFICER_OVERRIDE"
    REPORT_FINALIZED = "REPORT_FINALIZED"


class AuditEntry(Document):
    event_type: AuditEventType
    entity_id: str
    entity_type: str
    payload: dict
    prev_hash: str                 # SHA-256 of previous entry's content
    entry_hash: str                # SHA-256 of this entry's content (computed on save)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "audit_log"
        # Each entry's prev_hash must be unique: two concurrent writers that
        # both read the same chain head cannot both append — the loser gets a
        # DuplicateKeyError and re-reads the head. This makes the hash chain
        # race-safe across parallel Celery workers.
        indexes = [IndexModel([("prev_hash", ASCENDING)], unique=True,
                              name="uniq_prev_hash")]

    @staticmethod
    def compute_hash(event_type: str, entity_id: str, payload: dict,
                     prev_hash: str, created_at: datetime) -> str:
        content = json.dumps({
            "event_type": str(event_type),
            "entity_id": entity_id,
            "payload": payload,
            "prev_hash": prev_hash,
            "created_at": created_at.isoformat(),
        }, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()
