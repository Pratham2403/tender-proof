import asyncio
import json

from celery.result import AsyncResult
from fastapi import WebSocket

from app.worker import celery_app


class JobProgressManager:
    """
    Polls Celery task state and streams progress over WebSocket.
    Falls back gracefully if client disconnects.
    """

    async def stream(self, websocket: WebSocket, job_id: str):
        await websocket.accept()
        try:
            while True:
                result = AsyncResult(job_id, app=celery_app)
                state = result.state
                meta = result.info if isinstance(result.info, dict) else {}

                if state == "PROGRESS":
                    await websocket.send_text(json.dumps({
                        "type": "progress",
                        "pct": meta.get("pct", 0),
                        "message": meta.get("message", ""),
                    }))
                elif state == "SUCCESS":
                    await websocket.send_text(json.dumps({"type": "complete"}))
                    break
                elif state == "FAILURE":
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "reason": str(result.result),
                    }))
                    break
                else:
                    await websocket.send_text(json.dumps({
                        "type": "status",
                        "state": state,
                    }))

                await asyncio.sleep(1.5)
        except Exception:
            pass  # Client disconnected — no action needed
        finally:
            try:
                await websocket.close()
            except Exception:
                pass
