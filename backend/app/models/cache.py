from datetime import datetime

from beanie import Document
from pydantic import Field
from pymongo import ASCENDING, IndexModel

from app.models.bidder import CriterionExtraction


class ExtractionCache(Document):
    """
    Vision-extraction results keyed by document content hash + schema.

    If the same file (by SHA-256) appears in multiple bidder submissions —
    duplicate attachments are common in government bid packages — the
    extraction is reused instead of re-spending LLM calls (HLD §12,
    "Result caching").
    """

    file_sha256: str
    schema_id: str
    document_name: str            # Name the file had when first extracted
    page_count: int
    extractions: list[CriterionExtraction]
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "extraction_cache"
        indexes = [IndexModel(
            [("file_sha256", ASCENDING), ("schema_id", ASCENDING)],
            unique=True, name="uniq_file_schema",
        )]
