from datetime import datetime
from enum import Enum

from beanie import Document
from pydantic import BaseModel, Field


class BidderStatus(str, Enum):
    QUEUED = "QUEUED"
    EXTRACTING = "EXTRACTING"
    EVALUATING = "EVALUATING"
    EVALUATED = "EVALUATED"
    FAILED = "FAILED"


class Bidder(Document):
    tender_id: str
    company_name: str
    file_paths: list[str]
    status: BidderStatus = BidderStatus.QUEUED
    submitted_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "bidders"


class CriterionExtraction(BaseModel):
    criterion_id: str
    extracted_value: str | None       # None if not found on any page
    confidence: float                  # 0.0 – 1.0
    document_name: str | None = None
    page_number: int | None = None
    raw_text: str | None = None        # Verbatim passage supporting the extraction


class BidderProfile(Document):
    bidder_id: str
    schema_id: str
    extractions: list[CriterionExtraction] = []
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "bidder_profiles"

    def get_extraction(self, criterion_id: str) -> CriterionExtraction | None:
        return next((e for e in self.extractions if e.criterion_id == criterion_id), None)
