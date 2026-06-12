import asyncio
import random
from datetime import datetime

from pymongo.errors import DuplicateKeyError

from app.models.audit import AuditEntry, AuditEventType

MAX_APPEND_ATTEMPTS = 8


class AuditLogger:
    """
    Append-only, hash-chained audit log writer.
    No update or delete methods exist by design.

    Concurrency: a unique index on prev_hash guarantees only one writer can
    extend a given chain head. On contention the loser re-reads the head and
    retries, so parallel Celery workers can never fork the chain.
    """

    async def log(
        self,
        event_type: AuditEventType,
        entity_id: str,
        entity_type: str,
        payload: dict,
    ) -> AuditEntry:
        last_error: Exception | None = None
        for attempt in range(MAX_APPEND_ATTEMPTS):
            prev_hash = await self._get_last_hash()
            # Truncate to milliseconds: BSON stores millisecond precision, and
            # the hash must be reproducible from the round-tripped document.
            now = datetime.utcnow()
            created_at = now.replace(microsecond=(now.microsecond // 1000) * 1000)
            entry_hash = AuditEntry.compute_hash(
                event_type=event_type,
                entity_id=entity_id,
                payload=payload,
                prev_hash=prev_hash,
                created_at=created_at,
            )
            entry = AuditEntry(
                event_type=event_type,
                entity_id=entity_id,
                entity_type=entity_type,
                payload=payload,
                prev_hash=prev_hash,
                entry_hash=entry_hash,
                created_at=created_at,
            )
            try:
                await entry.insert()
                return entry
            except DuplicateKeyError as e:
                # Another writer appended to the same head — back off and retry
                last_error = e
                await asyncio.sleep(0.05 * (2 ** attempt) + random.random() * 0.05)
        raise RuntimeError(
            f"Audit append failed after {MAX_APPEND_ATTEMPTS} attempts under contention"
        ) from last_error

    async def verify_chain(self) -> bool:
        """Walk the full chain and confirm every link's hash is intact."""
        entries = await AuditEntry.find_all().sort("+_id").to_list()
        prev_hash = "GENESIS"
        for e in entries:
            if e.prev_hash != prev_hash:
                return False
            expected = AuditEntry.compute_hash(
                event_type=e.event_type, entity_id=e.entity_id,
                payload=e.payload, prev_hash=e.prev_hash, created_at=e.created_at,
            )
            if e.entry_hash != expected:
                return False
            prev_hash = e.entry_hash
        return True

    async def _get_last_hash(self) -> str:
        last = await AuditEntry.find_all().sort("-_id").first_or_none()
        return last.entry_hash if last else "GENESIS"
