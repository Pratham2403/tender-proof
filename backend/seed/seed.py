"""
Seed data loader.

Run once after starting MongoDB:
    cd backend && python -m seed.seed

Creates: 1 demo tender + 3 bidder submissions with varying document quality,
generating the mock PDFs first if they don't exist. The tender is inserted in
UPLOADING state; trigger compilation through the API/UI, or pass --compile to
enqueue the schema compilation task directly (requires Redis + worker).
"""

import asyncio
import sys
from pathlib import Path

from app.database import init_db
from app.models.bidder import Bidder
from app.models.tender import Tender, TenderStatus
from seed.generate_data import DATA_DIR, main as generate_files

DEMO_TENDER = {
    "title": "CRPF Demo Tender — Construction Services 2025",
    "file_path": str(DATA_DIR / "tender_demo.pdf"),
}

DEMO_BIDDERS = [
    {"company_name": "Apex Constructions Pvt Ltd",
     "files": [str(DATA_DIR / "bidder_a_typed.pdf")]},
    {"company_name": "BuildRight Engineers",
     "files": [str(DATA_DIR / "bidder_b_scanned.pdf")]},
    {"company_name": "GreenForm Infrastructure",
     "files": [str(DATA_DIR / "bidder_c_mixed.pdf"),
               str(DATA_DIR / "bidder_c_cert_photo.jpg")]},
]


async def seed(compile_now: bool = False):
    if not Path(DEMO_TENDER["file_path"]).exists():
        generate_files()

    await init_db()

    existing = await Tender.find_one(Tender.title == DEMO_TENDER["title"])
    if existing:
        print("Seed data already present. Skipping.")
        return

    tender = Tender(**DEMO_TENDER, status=TenderStatus.UPLOADING)
    await tender.insert()

    for b in DEMO_BIDDERS:
        bidder = Bidder(
            tender_id=str(tender.id),
            company_name=b["company_name"],
            file_paths=b["files"],
        )
        await bidder.insert()

    print(f"Seeded tender '{DEMO_TENDER['title']}' with {len(DEMO_BIDDERS)} bidders.")

    if compile_now:
        from app.tasks.compile_schema import compile_schema_task
        job = compile_schema_task.delay(str(tender.id))
        print(f"Enqueued schema compilation job {job.id}")


if __name__ == "__main__":
    asyncio.run(seed(compile_now="--compile" in sys.argv))
