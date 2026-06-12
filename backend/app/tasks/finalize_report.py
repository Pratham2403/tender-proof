import asyncio

from celery import shared_task

from app.database import init_db_sync
from app.models.audit import AuditEventType
from app.models.bidder import Bidder, BidderStatus
from app.models.tender import Tender, TenderStatus
from app.services.audit_logger import AuditLogger


@shared_task(bind=True)
def finalize_report_task(self, tender_id: str):
    asyncio.run(_finalize_report_async(tender_id))


async def _finalize_report_async(tender_id: str):
    await init_db_sync()
    bidders = await Bidder.find(Bidder.tender_id == tender_id).to_list()
    if not bidders:
        return

    pending = [b for b in bidders if b.status not in (BidderStatus.EVALUATED, BidderStatus.FAILED)]
    if pending:
        return  # Another bidder's evaluation will trigger finalization later

    tender = await Tender.get(tender_id)
    if tender.status == TenderStatus.COMPLETE:
        return  # Already finalized

    tender.status = TenderStatus.COMPLETE
    await tender.save()

    await AuditLogger().log(
        event_type=AuditEventType.REPORT_FINALIZED,
        entity_id=tender_id,
        entity_type="Tender",
        payload={
            "bidder_count": len(bidders),
            "evaluated": sum(1 for b in bidders if b.status == BidderStatus.EVALUATED),
            "failed": sum(1 for b in bidders if b.status == BidderStatus.FAILED),
        },
    )
