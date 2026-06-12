from typing import Any

from pydantic import BaseModel


class JobStatusResponse(BaseModel):
    job_id: str
    status: str            # PENDING | STARTED | PROGRESS | SUCCESS | FAILURE | RETRY
    progress_pct: int = 0
    message: str = ""
    result: Any = None
