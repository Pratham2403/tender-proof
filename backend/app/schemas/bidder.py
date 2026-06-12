from datetime import datetime

from pydantic import BaseModel

from app.models.bidder import BidderStatus


class BidderCreateResponse(BaseModel):
    bidder_id: str
    job_id: str


class BidderResponse(BaseModel):
    bidder_id: str
    tender_id: str
    company_name: str
    file_names: list[str]
    status: BidderStatus
    submitted_at: datetime
