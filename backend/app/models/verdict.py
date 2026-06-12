from datetime import datetime
from enum import Enum

from beanie import Document
from pydantic import Field


class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"


class VerdictRecord(Document):
    bidder_id: str
    tender_id: str
    schema_id: str
    criterion_id: str
    verdict: Verdict
    extracted_value: str | None
    document_name: str | None
    page_number: int | None
    raw_text: str | None
    rule_applied: str              # Human-readable rule description e.g. "turnover >= 5.0 Cr"
    reason: str                    # Why this verdict was reached
    confidence: float
    override_by: str | None = None
    override_reason: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "verdict_records"
