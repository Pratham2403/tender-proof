import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config import settings
from app.models.audit import AuditEventType
from app.models.bidder import Bidder
from app.models.tender import EvaluationSchema, SchemaStatus, Tender, TenderStatus
from app.schemas.tender import (
    SchemaApprovalRequest,
    SchemaApprovalResponse,
    SchemaResponse,
    TenderCreateResponse,
    TenderResponse,
)
from app.routers.common import fetch_or_404
from app.schemas.verdict import ConsolidatedReport
from app.services.audit_logger import AuditLogger
from app.services.report_builder import ReportBuilder
from app.tasks.compile_schema import compile_schema_task

router = APIRouter(prefix="/api/tenders", tags=["tenders"])

ALLOWED_TENDER_EXTENSIONS = {".pdf", ".docx", ".doc"}


@router.post("", status_code=202, response_model=TenderCreateResponse)
async def create_tender(
    title: str = Form(...),
    file: UploadFile = File(...),
) -> TenderCreateResponse:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_TENDER_EXTENSIONS:
        raise HTTPException(400, f"Unsupported tender file type: {suffix}. Allowed: PDF, DOCX")

    tender = Tender(title=title, file_path="", status=TenderStatus.UPLOADING)
    await tender.insert()
    tender_id = str(tender.id)

    upload_dir = Path(settings.upload_dir) / "tenders" / tender_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = str(upload_dir / Path(file.filename).name)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    tender.file_path = file_path
    await tender.save()

    job = compile_schema_task.delay(tender_id)
    return TenderCreateResponse(tender_id=tender_id, job_id=job.id)


@router.get("", response_model=list[TenderResponse])
async def list_tenders() -> list[TenderResponse]:
    tenders = await Tender.find_all().sort("-created_at").to_list()
    # Single aggregation instead of one count query per tender
    counts = {
        row["_id"]: row["n"]
        for row in await Bidder.aggregate(
            [{"$group": {"_id": "$tender_id", "n": {"$sum": 1}}}]
        ).to_list()
    }
    return [
        TenderResponse(
            tender_id=str(t.id), title=t.title, status=t.status,
            created_at=t.created_at, bidder_count=counts.get(str(t.id), 0),
        )
        for t in tenders
    ]


@router.get("/{tender_id}", response_model=TenderResponse)
async def get_tender(tender_id: str) -> TenderResponse:
    tender = await fetch_or_404(Tender, tender_id, "Tender")
    bidder_count = await Bidder.find(Bidder.tender_id == tender_id).count()
    return TenderResponse(
        tender_id=tender_id, title=tender.title, status=tender.status,
        created_at=tender.created_at, bidder_count=bidder_count,
    )


@router.get("/{tender_id}/schema", response_model=SchemaResponse)
async def get_schema(tender_id: str) -> SchemaResponse:
    schema = await EvaluationSchema.find_one(EvaluationSchema.tender_id == tender_id)
    if not schema:
        raise HTTPException(404, "Schema not found — compilation may still be running")
    return SchemaResponse(
        schema_id=str(schema.id), tender_id=tender_id, criteria=schema.criteria,
        status=schema.status, approved_by=schema.approved_by,
        approved_at=schema.approved_at, compiled_at=schema.compiled_at,
    )


@router.patch("/{tender_id}/schema", response_model=SchemaApprovalResponse)
async def approve_schema(tender_id: str, body: SchemaApprovalRequest) -> SchemaApprovalResponse:
    schema = await EvaluationSchema.find_one(EvaluationSchema.tender_id == tender_id)
    if not schema:
        raise HTTPException(404, "Schema not found")

    if body.criteria:  # Officer edited criteria
        schema.criteria = body.criteria

    schema.status = SchemaStatus.APPROVED
    schema.approved_by = "officer"  # Extend with real auth when needed
    schema.approved_at = datetime.utcnow()
    await schema.save()

    tender = await fetch_or_404(Tender, tender_id, "Tender")
    tender.status = TenderStatus.APPROVED
    await tender.save()

    await AuditLogger().log(
        event_type=AuditEventType.SCHEMA_APPROVED,
        entity_id=str(schema.id),
        entity_type="EvaluationSchema",
        payload={"approved_by": schema.approved_by, "criteria_count": len(schema.criteria)},
    )
    return SchemaApprovalResponse(schema_id=str(schema.id), approved_at=schema.approved_at)


@router.get("/{tender_id}/report", response_model=ConsolidatedReport)
async def get_report(tender_id: str) -> ConsolidatedReport:
    await fetch_or_404(Tender, tender_id, "Tender")
    schema = await EvaluationSchema.find_one(EvaluationSchema.tender_id == tender_id)
    if not schema:
        raise HTTPException(404, "Schema not found")
    return await ReportBuilder().build(tender_id, schema)
