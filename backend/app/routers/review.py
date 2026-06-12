from fastapi import APIRouter, HTTPException

from app.models.audit import AuditEventType
from app.models.bidder import Bidder
from app.models.tender import EvaluationSchema
from app.models.verdict import Verdict, VerdictRecord
from app.schemas.verdict import ReviewItem, ReviewResolveRequest
from app.services.audit_logger import AuditLogger

router = APIRouter(prefix="/api/tenders/{tender_id}/review", tags=["review"])


@router.get("", response_model=list[ReviewItem])
async def get_review_queue(tender_id: str) -> list[ReviewItem]:
    records = await VerdictRecord.find(
        VerdictRecord.tender_id == tender_id,
        VerdictRecord.verdict == Verdict.REVIEW,
        VerdictRecord.override_by == None,  # noqa: E711
    ).to_list()

    schema = await EvaluationSchema.find_one(EvaluationSchema.tender_id == tender_id)
    criteria_map = {c.criterion_id: c for c in (schema.criteria if schema else [])}

    bidder_ids = {r.bidder_id for r in records}
    bidder_names = {}
    for bid in bidder_ids:
        bidder = await Bidder.get(bid)
        bidder_names[bid] = bidder.company_name if bidder else "Unknown"

    items = []
    for r in records:
        criterion = criteria_map.get(r.criterion_id)
        items.append(ReviewItem(
            item_id=str(r.id),
            bidder_id=r.bidder_id,
            company_name=bidder_names.get(r.bidder_id, "Unknown"),
            criterion_id=r.criterion_id,
            label=criterion.label if criterion else r.criterion_id,
            mandatory=criterion.mandatory if criterion else False,
            extracted_value=r.extracted_value,
            document_name=r.document_name,
            page_number=r.page_number,
            raw_text=r.raw_text,
            reason=r.reason,
            confidence=r.confidence,
            created_at=r.created_at,
        ))

    # Rank by impact × uncertainty: mandatory uncertain items first
    items.sort(key=lambda i: (2 if i.mandatory else 1) * (1 - i.confidence), reverse=True)
    return items


@router.post("/{item_id}")
async def resolve_review_item(tender_id: str, item_id: str, body: ReviewResolveRequest):
    record = await VerdictRecord.get(item_id)
    if not record or record.tender_id != tender_id:
        raise HTTPException(404, "Review item not found")
    if body.verdict not in (Verdict.PASS, Verdict.FAIL):
        raise HTTPException(400, "Resolved verdict must be PASS or FAIL")

    record.verdict = body.verdict
    record.override_by = "officer"
    record.override_reason = body.reason
    await record.save()

    await AuditLogger().log(
        event_type=AuditEventType.OFFICER_OVERRIDE,
        entity_id=item_id,
        entity_type="VerdictRecord",
        payload={
            "action": body.action,
            "new_verdict": record.verdict,
            "reason": record.override_reason,
            "criterion_id": record.criterion_id,
            "bidder_id": record.bidder_id,
        },
    )
    return {
        "item_id": item_id,
        "verdict": record.verdict,
        "override_by": record.override_by,
        "override_reason": record.override_reason,
    }
