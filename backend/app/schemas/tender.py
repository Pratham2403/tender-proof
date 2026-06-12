from datetime import datetime

from pydantic import BaseModel

from app.models.tender import Criterion, SchemaStatus, TenderStatus


class TenderCreateResponse(BaseModel):
    tender_id: str
    job_id: str


class TenderResponse(BaseModel):
    tender_id: str
    title: str
    status: TenderStatus
    created_at: datetime
    bidder_count: int = 0


class SchemaResponse(BaseModel):
    schema_id: str
    tender_id: str
    criteria: list[Criterion]
    status: SchemaStatus
    approved_by: str | None
    approved_at: datetime | None
    compiled_at: datetime


class SchemaApprovalRequest(BaseModel):
    action: str = "approve"  # "approve" | "edit_and_approve"
    criteria: list[Criterion] | None = None


class SchemaApprovalResponse(BaseModel):
    schema_id: str
    approved_at: datetime
