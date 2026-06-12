import asyncio

from celery import shared_task

from app.database import init_db_sync
from app.models.audit import AuditEventType
from app.models.bidder import Bidder, BidderProfile, BidderStatus
from app.models.tender import EvaluationSchema
from app.models.verdict import VerdictRecord
from app.services.audit_logger import AuditLogger
from app.services.rule_engine import RuleEngine


@shared_task(bind=True)
def evaluate_bidder_task(self, bidder_id: str, schema_id: str):
    asyncio.run(_evaluate_bidder_async(bidder_id, schema_id))


async def _evaluate_bidder_async(bidder_id: str, schema_id: str):
    await init_db_sync()
    bidder = await Bidder.get(bidder_id)
    schema = await EvaluationSchema.get(schema_id)
    profile = await BidderProfile.find_one(BidderProfile.bidder_id == bidder_id)

    # Idempotent re-run: clear any verdicts left behind by a prior attempt
    await VerdictRecord.find(VerdictRecord.bidder_id == bidder_id).delete()

    engine = RuleEngine()
    audit = AuditLogger()

    for criterion in schema.criteria:
        extraction = profile.get_extraction(criterion.criterion_id) if profile else None
        verdict_record = engine.evaluate_criterion(
            criterion=criterion,
            extraction=extraction,
            bidder_id=bidder_id,
            tender_id=bidder.tender_id,
            schema_id=schema_id,
        )
        await verdict_record.insert()
        await audit.log(
            event_type=AuditEventType.VERDICT_PRODUCED,
            entity_id=str(verdict_record.id),
            entity_type="VerdictRecord",
            payload={
                "criterion_id": criterion.criterion_id,
                "verdict": verdict_record.verdict,
                "confidence": verdict_record.confidence,
            },
        )

    bidder.status = BidderStatus.EVALUATED
    await bidder.save()

    # If every bidder for this tender is now evaluated, finalize the report
    from app.tasks.finalize_report import finalize_report_task
    finalize_report_task.delay(bidder.tender_id)
