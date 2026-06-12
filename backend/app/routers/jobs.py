from celery.result import AsyncResult
from fastapi import APIRouter

from app.schemas.job import JobStatusResponse
from app.worker import celery_app

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(job_id: str) -> JobStatusResponse:
    result = AsyncResult(job_id, app=celery_app)
    state = result.state
    meta = result.info if isinstance(result.info, dict) else {}

    if state == "PROGRESS":
        return JobStatusResponse(
            job_id=job_id, status=state,
            progress_pct=meta.get("pct", 0), message=meta.get("message", ""),
        )
    if state == "SUCCESS":
        return JobStatusResponse(job_id=job_id, status=state, progress_pct=100)
    if state == "FAILURE":
        return JobStatusResponse(job_id=job_id, status=state, message=str(result.result))
    return JobStatusResponse(job_id=job_id, status=state)
