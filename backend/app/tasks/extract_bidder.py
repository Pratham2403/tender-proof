import asyncio
import hashlib
import logging
from datetime import datetime
from pathlib import Path

from celery import shared_task
from pymongo.errors import DuplicateKeyError

from app.database import init_db_sync
from app.models.audit import AuditEventType
from app.models.bidder import Bidder, BidderProfile, BidderStatus, CriterionExtraction
from app.models.cache import ExtractionCache
from app.models.tender import EvaluationSchema
from app.services.audit_logger import AuditLogger
from app.services.document_converter import DocumentConverter
from app.services.vision_extractor import VisionExtractor

logger = logging.getLogger("tenderproof.tasks.extract_bidder")


@shared_task(bind=True, max_retries=5, default_retry_delay=60)
def extract_bidder_task(self, bidder_id: str, schema_id: str):
    asyncio.run(_extract_bidder_async(self, bidder_id, schema_id))


def _merge_best(best: dict[str, CriterionExtraction],
                extractions: list[CriterionExtraction]) -> None:
    """Keep the highest-confidence extraction with a value per criterion."""
    for ext in extractions:
        existing = best.get(ext.criterion_id)
        if existing is None or (ext.extracted_value and ext.confidence > existing.confidence):
            best[ext.criterion_id] = ext


async def _extract_file(
    task, extractor: VisionExtractor, converter: DocumentConverter,
    file_path: str, schema: EvaluationSchema,
    progress: tuple[int, int],
) -> tuple[list[CriterionExtraction], int]:
    """
    Extract one document, page by page. Returns (best extractions for this
    file, page count). Blank pages are skipped before any LLM call.
    """
    file_name = Path(file_path).name
    pages = converter.convert(file_path)
    file_best: dict[str, CriterionExtraction] = {}

    for page_num, page_png in pages:
        file_index, total_files = progress
        task.update_state(state="PROGRESS", meta={
            "pct": int((file_index + page_num / max(len(pages), 1)) / total_files * 100),
            "message": f"Extracting {file_name} page {page_num}/{len(pages)}",
        })
        if DocumentConverter.is_blank_page(page_png):
            logger.info("skipping blank page %s p.%d", file_name, page_num)
            continue
        page_extractions = await extractor.extract_page(
            page_png_bytes=page_png, criteria=schema.criteria,
        )
        for ext in page_extractions:
            ext.document_name = file_name
            ext.page_number = page_num
        _merge_best(file_best, page_extractions)

    return list(file_best.values()), len(pages)


async def _extract_bidder_async(task, bidder_id: str, schema_id: str):
    await init_db_sync()
    bidder = await Bidder.get(bidder_id)
    schema = await EvaluationSchema.get(schema_id)

    bidder.status = BidderStatus.EXTRACTING
    await bidder.save()
    logger.info("extraction started bidder=%s tender=%s files=%d",
                bidder_id, bidder.tender_id, len(bidder.file_paths))

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
        total_files = len(bidder.file_paths) or 1
        for file_index, file_path in enumerate(bidder.file_paths):
            file_name = Path(file_path).name
            file_sha256 = hashlib.sha256(Path(file_path).read_bytes()).hexdigest()

            cached = await ExtractionCache.find_one(
                ExtractionCache.file_sha256 == file_sha256,
                ExtractionCache.schema_id == schema_id,
            )
            if cached:
                logger.info("extraction cache hit file=%s (first seen as %s)",
                            file_name, cached.document_name)
                file_extractions = [e.model_copy(update={"document_name": file_name})
                                    for e in cached.extractions]
            else:
                file_extractions, page_count = await _extract_file(
                    task, extractor, converter, file_path, schema,
                    progress=(file_index, total_files),
                )
                try:
                    await ExtractionCache(
                        file_sha256=file_sha256, schema_id=schema_id,
                        document_name=file_name, page_count=page_count,
                        extractions=file_extractions,
                    ).insert()
                except DuplicateKeyError:
                    pass  # Concurrent worker cached the same file first

            _merge_best(best_extractions, file_extractions)

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
        logger.info("extraction complete bidder=%s criteria=%d",
                    bidder_id, len(profile.extractions))

        # Chain to evaluation task
        from app.tasks.evaluate_bidder import evaluate_bidder_task
        evaluate_bidder_task.delay(bidder_id, schema_id)

    except Exception as exc:
        logger.exception("extraction failed bidder=%s", bidder_id)
        bidder.status = BidderStatus.FAILED
        await bidder.save()
        raise task.retry(exc=exc)
