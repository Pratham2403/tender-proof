"""
Serves the real FastAPI app on :8000 with an in-memory database populated by
the same stubbed pipeline the smoke test uses — handy for exercising the
frontend without MongoDB or LLM keys.

Run:  cd backend && python -m tests.demo_server
"""

import asyncio
from unittest.mock import patch

import httpx
import uvicorn
from beanie import init_beanie
from mongomock_motor import AsyncMongoMockClient

import app.main as main_mod
from app.database import DOCUMENT_MODELS
from seed.generate_data import DATA_DIR, main as generate_seed_files
from tests.smoke_e2e import (
    FakeTask,
    StubSchemaCompiler,
    noop_init_db,
    run_pipeline_for_bidder,
)


async def populate():
    transport = httpx.ASGITransport(app=main_mod.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://x") as http:
        with open(DATA_DIR / "tender_demo.pdf", "rb") as f:
            r = await http.post(
                "/api/tenders",
                data={"title": "CRPF Demo Tender — Construction Services 2025"},
                files={"file": ("tender_demo.pdf", f, "application/pdf")},
            )
        tender_id = r.json()["tender_id"]

        import app.tasks.compile_schema as compile_mod
        with patch.object(compile_mod, "init_db_sync", noop_init_db), \
             patch.object(compile_mod, "SchemaCompiler", StubSchemaCompiler):
            await compile_mod._compile_schema_async(FakeTask(), tender_id)

        r = await http.get(f"/api/tenders/{tender_id}/schema")
        schema_id = r.json()["schema_id"]
        await http.patch(f"/api/tenders/{tender_id}/schema", json={"action": "approve"})

        bidder_files = {
            "Apex Constructions Pvt Ltd": ["bidder_a_typed.pdf"],
            "BuildRight Engineers": ["bidder_b_scanned.pdf"],
            "GreenForm Infrastructure": ["bidder_c_mixed.pdf", "bidder_c_cert_photo.jpg"],
        }
        for company, names in bidder_files.items():
            files = [("files", (n, open(DATA_DIR / n, "rb"),
                                "application/octet-stream")) for n in names]
            r = await http.post(f"/api/tenders/{tender_id}/bidders",
                                data={"company_name": company}, files=files)
            await run_pipeline_for_bidder(r.json()["bidder_id"], schema_id, company)

        print(f"Demo data ready — tender {tender_id}")
        return tender_id


async def main():
    generate_seed_files()
    client = AsyncMongoMockClient()
    await init_beanie(database=client.tenderproof_demo,
                      document_models=DOCUMENT_MODELS)

    # The lifespan would re-init Beanie against a real MongoDB URL; keep the
    # mongomock binding instead.
    async def keep_mongomock():
        pass

    main_mod.init_db = keep_mongomock

    await populate()

    config = uvicorn.Config(main_mod.app, host="127.0.0.1", port=8000,
                            log_level="warning")
    print("Serving API on http://127.0.0.1:8000")
    await uvicorn.Server(config).serve()


if __name__ == "__main__":
    asyncio.run(main())
