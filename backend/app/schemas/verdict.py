from datetime import datetime

from pydantic import BaseModel

from app.models.verdict import Verdict


class CriterionVerdict(BaseModel):
    criterion_id: str
    label: str
    mandatory: bool
    verdict: Verdict
    extracted_value: str | None
    document_name: str | None
    page_number: int | None
    reason: str
    confidence: float
    rule_applied: str | None = None
    override_by: str | None = None


class BidderSummary(BaseModel):
    bidder_id: str
    company_name: str
    overall_verdict: Verdict
    criteria_verdicts: list[CriterionVerdict]


class ConsolidatedReport(BaseModel):
    tender_id: str
    bidder_summaries: list[BidderSummary]


class ReviewItem(BaseModel):
    item_id: str
    bidder_id: str
    company_name: str
    criterion_id: str
    label: str
    mandatory: bool
    extracted_value: str | None
    document_name: str | None
    page_number: int | None
    raw_text: str | None
    reason: str
    confidence: float
    created_at: datetime


class ReviewResolveRequest(BaseModel):
    action: str = "confirm"  # "confirm" | "override"
    verdict: Verdict
    reason: str = ""
