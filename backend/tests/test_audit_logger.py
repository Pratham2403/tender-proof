import pytest

from app.models.audit import AuditEntry, AuditEventType
from app.services.audit_logger import AuditLogger


@pytest.mark.asyncio
async def test_first_entry_chains_from_genesis(db):
    logger = AuditLogger()
    entry = await logger.log(AuditEventType.SCHEMA_COMPILED, "e1", "EvaluationSchema",
                             {"criteria_count": 5})
    assert entry.prev_hash == "GENESIS"
    assert entry.entry_hash


@pytest.mark.asyncio
async def test_entries_form_a_hash_chain(db):
    logger = AuditLogger()
    e1 = await logger.log(AuditEventType.SCHEMA_COMPILED, "e1", "EvaluationSchema", {})
    e2 = await logger.log(AuditEventType.SCHEMA_APPROVED, "e1", "EvaluationSchema", {})
    e3 = await logger.log(AuditEventType.VERDICT_PRODUCED, "v1", "VerdictRecord", {})
    assert e2.prev_hash == e1.entry_hash
    assert e3.prev_hash == e2.entry_hash
    assert await logger.verify_chain() is True


@pytest.mark.asyncio
async def test_tampering_breaks_the_chain(db):
    logger = AuditLogger()
    e1 = await logger.log(AuditEventType.SCHEMA_COMPILED, "e1", "EvaluationSchema",
                          {"criteria_count": 5})
    await logger.log(AuditEventType.SCHEMA_APPROVED, "e1", "EvaluationSchema", {})

    # Tamper with the first entry's payload behind the logger's back
    raw = await AuditEntry.get(e1.id)
    raw.payload = {"criteria_count": 99}
    await raw.save()

    assert await logger.verify_chain() is False
