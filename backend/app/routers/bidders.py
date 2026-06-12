import shutil
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config import settings
from app.models.bidder import Bidder
from app.models.tender import EvaluationSchema, SchemaStatus, Tender, TenderStatus
from app.routers.common import fetch_or_404
from app.schemas.bidder import BidderCreateResponse, BidderResponse
from app.tasks.extract_bidder import extract_bidder_task

router = APIRouter(prefix="/api/tenders/{tender_id}/bidders", tags=["bidders"])

ALLOWED_BIDDER_EXTENSIONS = {".pdf", ".docx", ".doc", ".jpg", ".jpeg", ".png", ".webp"}


@router.post("", status_code=202, response_model=BidderCreateResponse)
async def create_bidder(
    tender_id: str,
    company_name: str = Form(...),
    files: list[UploadFile] = File(...),
) -> BidderCreateResponse:
    tender = await fetch_or_404(Tender, tender_id, "Tender")

    schema = await EvaluationSchema.find_one(EvaluationSchema.tender_id == tender_id)
    if not schema or schema.status != SchemaStatus.APPROVED:
        raise HTTPException(409, "Evaluation schema must be approved before uploading bidders")

    for f in files:
        suffix = Path(f.filename or "").suffix.lower()
        if suffix not in ALLOWED_BIDDER_EXTENSIONS:
            raise HTTPException(400, f"Unsupported file type: {suffix}")

    bidder = Bidder(tender_id=tender_id, company_name=company_name, file_paths=[])
    await bidder.insert()
    bidder_id = str(bidder.id)

    upload_dir = Path(settings.upload_dir) / "bidders" / bidder_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_paths = []
    for f in files:
        file_path = str(upload_dir / Path(f.filename).name)
        with open(file_path, "wb") as out:
            shutil.copyfileobj(f.file, out)
        file_paths.append(file_path)

    bidder.file_paths = file_paths
    await bidder.save()

    if tender.status in (TenderStatus.APPROVED, TenderStatus.COMPLETE):
        tender.status = TenderStatus.EVALUATING
        await tender.save()

    job = extract_bidder_task.delay(bidder_id, str(schema.id))
    return BidderCreateResponse(bidder_id=bidder_id, job_id=job.id)


@router.get("", response_model=list[BidderResponse])
async def list_bidders(tender_id: str) -> list[BidderResponse]:
    bidders = await Bidder.find(Bidder.tender_id == tender_id).sort("+submitted_at").to_list()
    return [
        BidderResponse(
            bidder_id=str(b.id), tender_id=tender_id, company_name=b.company_name,
            file_names=[Path(p).name for p in b.file_paths],
            status=b.status, submitted_at=b.submitted_at,
        )
        for b in bidders
    ]
