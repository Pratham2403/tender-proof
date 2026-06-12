import asyncio
import logging

from celery import shared_task

logger = logging.getLogger("tenderproof.tasks.compile_schema")

from app.database import init_db_sync
from app.models.audit import AuditEventType
from app.models.tender import EvaluationSchema, SchemaStatus, Tender, TenderStatus
from app.services.audit_logger import AuditLogger
from app.services.document_converter import DocumentConverter
from app.services.schema_compiler import SchemaCompiler


@shared_task(bind=True, max_retries=5, default_retry_delay=30)
def compile_schema_task(self, tender_id: str):
    asyncio.run(_compile_schema_async(self, tender_id))


async def _compile_schema_async(task, tender_id: str):
    await init_db_sync()
    tender = await Tender.get(tender_id)
    tender.status = TenderStatus.COMPILING
    await tender.save()
    logger.info("schema compilation started tender=%s", tender_id)

    try:
        task.update_state(state="PROGRESS", meta={"pct": 10, "message": "Extracting tender text"})
        converter = DocumentConverter()
        tender_text = converter.extract_text(tender.file_path)

        task.update_state(state="PROGRESS", meta={"pct": 40, "message": "Compiling eligibility schema"})
        compiler = SchemaCompiler()
        criteria = await compiler.compile(tender_text)

        schema = EvaluationSchema(
            tender_id=tender_id,
            criteria=criteria,
            status=SchemaStatus.PENDING_APPROVAL,
        )
        await schema.insert()

        tender.status = TenderStatus.PENDING_APPROVAL
        await tender.save()

        audit = AuditLogger()
        await audit.log(
            event_type=AuditEventType.SCHEMA_COMPILED,
            entity_id=str(schema.id),
            entity_type="EvaluationSchema",
            payload={"tender_id": tender_id, "criteria_count": len(criteria)},
        )
        task.update_state(state="PROGRESS", meta={"pct": 100, "message": "Schema ready for review"})
        logger.info("schema compiled tender=%s criteria=%d", tender_id, len(criteria))

    except Exception as exc:
        logger.exception("schema compilation failed tender=%s", tender_id)
        tender.status = TenderStatus.FAILED
        await tender.save()
        raise task.retry(exc=exc)
