from beanie import Document
from fastapi import HTTPException


async def fetch_or_404(model: type[Document], doc_id: str, label: str) -> Document:
    """
    Beanie's get() raises on malformed ObjectIds; clients should see a clean
    404 for any id that doesn't resolve, malformed or merely absent.
    """
    try:
        doc = await model.get(doc_id)
    except Exception:
        doc = None
    if doc is None:
        raise HTTPException(404, f"{label} not found")
    return doc
