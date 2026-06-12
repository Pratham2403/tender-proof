import asyncio
from datetime import datetime
from pathlib import Path

from celery import shared_task

from app.database import init_db_sync
from app.models.audit import AuditEventType
from app.models.bidder import Bidder, BidderProfile, BidderStatus, CriterionExtraction
from app.models.tender import EvaluationSchema
from app.services.audit_logger import AuditLogger
from app.services.document_converter import DocumentConverter
from app.services.vision_extractor import VisionExtractor


@shared_task(bind=True, max_retries=5, default_retry_delay=60)
def extract_bidder_task(self, bidder_id: str, schema_id: str):
    asyncio.run(_extract_bidder_async(self, bidder_id, schema_id))


async def _extract_bidder_async(task, bidder_id: str, schema_id: str):
    await init_db_sync()
    bidder = await Bidder.get(bidder_id)
    schema = await EvaluationSchema.get(schema_id)

    bidder.status = BidderStatus.EXTRACTING
    await bidder.save()

    # Idempotent re-run: reuse the existing profile if a retry left one behind
    profile = await BidderProfile.find_one(BidderProfile.bidder_id == bidder_id)
    if profile is None:
        profile = BidderProfile(bidder_id=bidder_id, schema_id=schema_id)
        await profile.insert()

    converter = DocumentConverter()
    extractor = VisionExtractor()

    # Best extraction per criterion across all pages and files
    best_extractions: dict[str, CriterionExtraction] = {}

    try:
        all_pages: list[tuple[str, int, bytes]] = []
        for file_path in bidder.file_paths:
            file_name = Path(file_path).name
            for page_num, page_png in converter.convert(file_path):
                all_pages.append((file_name, page_num, page_png))

        total = len(all_pages) or 1
        for i, (file_name, page_num, page_png) in enumerate(all_pages):
            task.update_state(state="PROGRESS", meta={
                "pct": int(i / total * 100),
                "message": f"Extracting {file_name} page {page_num}",
            })
            page_extractions = await extractor.extract_page(
                page_png_bytes=page_png,
                criteria=schema.criteria,
            )
            for ext in page_extractions:
                ext.document_name = file_name
                ext.page_number = page_num
                existing = best_extractions.get(ext.criterion_id)
                if existing is None or (ext.extracted_value and ext.confidence > existing.confidence):
                    best_extractions[ext.criterion_id] = ext

        profile.extractions = list(best_extractions.values())
        profile.updated_at = datetime.utcnow()
        await profile.save()

        bidder.status = BidderStatus.EVALUATING
        await bidder.save()

        audit = AuditLogger()
        await audit.log(
            event_type=AuditEventType.EXTRACTION_COMPLETE,
            entity_id=bidder_id,
            entity_type="Bidder",
            payload={"schema_id": schema_id, "criteria_extracted": len(profile.extractions)},
        )

        # Chain to evaluation task
        from app.tasks.evaluate_bidder import evaluate_bidder_task
        evaluate_bidder_task.delay(bidder_id, schema_id)

    except Exception as exc:
        bidder.status = BidderStatus.FAILED
        await bidder.save()
        raise task.retry(exc=exc)
