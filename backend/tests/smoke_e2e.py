"""
End-to-end smoke test of the full TenderProof pipeline.

Runs the real FastAPI app in-process (httpx ASGI transport) against an
in-memory MongoDB (mongomock), with real document conversion of the seed
PDFs/JPG and the real rule engine, audit logger, and report builder. Only
the two external LLM calls (Gemini schema compilation, Qwen vision
extraction) are stubbed — everything else is the production code path.

Run:  cd backend && python -m tests.smoke_e2e
"""

import asyncio
from pathlib import Path
from unittest.mock import patch

import httpx
from beanie import init_beanie
from mongomock_motor import AsyncMongoMockClient

from app.database import DOCUMENT_MODELS
from app.main import app
from app.models.bidder import CriterionExtraction
from app.models.tender import (
    BooleanPresenceParams,
    CountMinimumParams,
    Criterion,
    CriterionType,
    CurrencyThresholdParams,
    DateRangeParams,
    SimilarityScoreParams,
)
from app.services.audit_logger import AuditLogger
from seed.generate_data import DATA_DIR, main as generate_seed_files

PASSED: list[str] = []


def check(name: str, condition: bool, detail: str = ""):
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))
    if not condition:
        raise AssertionError(f"Smoke check failed: {name} {detail}")
    PASSED.append(name)


# ---------------------------------------------------------------- LLM stubs

DEMO_CRITERIA = [
    Criterion(criterion_id="C-01", label="Annual Turnover Minimum",
              criterion_type=CriterionType.CURRENCY_THRESHOLD, mandatory=True,
              params=CurrencyThresholdParams(minimum_crore=5.0),
              accepted_evidence=["audited balance sheet", "CA certificate"],
              source_text="minimum average annual turnover of Rs. 5.00 Crore"),
    Criterion(criterion_id="C-02", label="Similar Projects Completed",
              criterion_type=CriterionType.COUNT_MINIMUM, mandatory=True,
              params=CountMinimumParams(minimum_count=3, within_years=5),
              accepted_evidence=["work completion certificates"],
              source_text="at least 3 similar construction projects within the last 5 years"),
    Criterion(criterion_id="C-03", label="GST Registration",
              criterion_type=CriterionType.BOOLEAN_PRESENCE, mandatory=True,
              params=BooleanPresenceParams(accepted_values=["GST", "GSTIN"]),
              accepted_evidence=["GST certificate"],
              source_text="valid GST registration certificate (GSTIN)"),
    Criterion(criterion_id="C-04", label="ISO 9001 Validity",
              criterion_type=CriterionType.DATE_RANGE, mandatory=True,
              params=DateRangeParams(not_expired_as_of="2025-03-31T00:00:00"),
              accepted_evidence=["ISO 9001 certificate"],
              source_text="valid ISO 9001 ... not expired as of 31 March 2025"),
    Criterion(criterion_id="C-05", label="Similar Project Experience",
              criterion_type=CriterionType.SIMILARITY_SCORE, mandatory=True,
              params=SimilarityScoreParams(
                  description="construction of institutional or government buildings"),
              accepted_evidence=["work portfolio"],
              source_text="prior experience executing projects of a similar nature"),
    Criterion(criterion_id="C-06", label="MSME / Udyam Registration",
              criterion_type=CriterionType.BOOLEAN_PRESENCE, mandatory=False,
              params=BooleanPresenceParams(accepted_values=["MSME", "UDYAM"]),
              accepted_evidence=["Udyam certificate"],
              source_text="may optionally furnish an MSME / Udyam registration"),
]


class StubSchemaCompiler:
    """Stands in for the Gemini call; returns the demo tender's criteria."""

    async def compile(self, tender_text: str) -> list[Criterion]:
        assert "ELIGIBILITY CRITERIA" in tender_text, \
            "real text extraction should have run on the tender PDF"
        return DEMO_CRITERIA


# (value, confidence) per criterion, per bidder — simulates Qwen output
STUB_PROFILES = {
    "Apex Constructions Pvt Ltd": {
        "C-01": ("8.45", 0.92), "C-02": ("5", 0.90),
        "C-03": ("GSTIN 27AAACA1234F1Z5", 0.95), "C-04": ("2026-08-14", 0.90),
        "C-05": ("0.85", 0.88), "C-06": ("UDYAM-MH-04-0012345", 0.90),
    },
    "BuildRight Engineers": {
        "C-01": ("3.20", 0.81), "C-02": ("2", 0.75),
        "C-03": ("GSTIN 23AABCB9876K2Z1", 0.72), "C-04": ("2024-11-30", 0.65),
        "C-05": ("0.55", 0.80), "C-06": (None, 0.0),
    },
    "GreenForm Infrastructure": {
        "C-01": ("6.10", 0.90), "C-02": ("4", 0.85),
        "C-03": ("GSTIN 08AAGCG4567L1Z9", 0.90), "C-04": ("2027-01-20", 0.55),
        "C-05": ("0.80", 0.85), "C-06": (None, 0.0),
    },
}


class StubVisionExtractor:
    """Stands in for the Qwen vision call; serves the current bidder's values."""

    current_company: str = ""

    async def extract_page(self, page_png_bytes: bytes, criteria):
        assert page_png_bytes[:8] == b"\x89PNG\r\n\x1a\n", \
            "real document conversion should hand the extractor PNG pages"
        profile = STUB_PROFILES[self.current_company]
        out = []
        for c in criteria:
            value, conf = profile.get(c.criterion_id, (None, 0.0))
            out.append(CriterionExtraction(
                criterion_id=c.criterion_id, extracted_value=value,
                confidence=conf, raw_text=f"stub passage for {c.criterion_id}",
            ))
        return out


class FakeTask:
    """Minimal stand-in for the bound Celery task in direct invocation."""

    def update_state(self, **kwargs):
        pass

    def retry(self, exc=None, **kwargs):
        raise exc if exc else RuntimeError("task retry requested")


async def noop_init_db():
    pass  # Beanie is already initialized against mongomock


# ---------------------------------------------------------------- pipeline


async def run_pipeline_for_bidder(bidder_id: str, schema_id: str, company: str):
    """Drive extract → evaluate → finalize in-process with stubbed LLMs."""
    import app.tasks.evaluate_bidder as eval_mod
    import app.tasks.extract_bidder as extract_mod
    import app.tasks.finalize_report as finalize_mod

    StubVisionExtractor.current_company = company
    chained: list[tuple] = []

    with patch.object(extract_mod, "init_db_sync", noop_init_db), \
         patch.object(extract_mod, "VisionExtractor", StubVisionExtractor), \
         patch.object(eval_mod.evaluate_bidder_task, "delay",
                      lambda *a: chained.append(("evaluate", a))):
        await extract_mod._extract_bidder_async(FakeTask(), bidder_id, schema_id)
    check(f"extraction chained to evaluation ({company})", len(chained) == 1)

    with patch.object(eval_mod, "init_db_sync", noop_init_db), \
         patch.object(finalize_mod.finalize_report_task, "delay",
                      lambda *a: chained.append(("finalize", a))):
        await eval_mod._evaluate_bidder_async(bidder_id, schema_id)

    with patch.object(finalize_mod, "init_db_sync", noop_init_db):
        await finalize_mod._finalize_report_async(chained[-1][1][0])


async def main():
    generate_seed_files()

    client = AsyncMongoMockClient()
    await init_beanie(database=client.tenderproof_smoke,
                      document_models=DOCUMENT_MODELS)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport,
                                 base_url="http://test") as http:

        print("\n== 1. Health & empty dashboard ==")
        # mongomock can't answer a real `ping`, so health reports degraded
        # here; what matters is the endpoint responds and reports components
        r = await http.get("/api/health")
        check("GET /api/health responds with component states",
              r.status_code == 200 and {"mongo", "redis"} <= r.json().keys())
        r = await http.get("/api/tenders")
        check("GET /api/tenders (empty)", r.status_code == 200 and r.json() == [])

        print("\n== 2. Tender upload → schema compilation ==")
        with open(DATA_DIR / "tender_demo.pdf", "rb") as f:
            r = await http.post(
                "/api/tenders",
                data={"title": "CRPF Demo Tender — Construction Services 2025"},
                files={"file": ("tender_demo.pdf", f, "application/pdf")},
            )
        check("POST /api/tenders accepted", r.status_code == 202, r.text)
        tender_id = r.json()["tender_id"]
        check("job id returned", bool(r.json()["job_id"]))

        r = await http.post("/api/tenders", data={"title": "bad"},
                            files={"file": ("x.xlsx", b"zz", "application/zip")})
        check("rejects unsupported tender file type", r.status_code == 400)

        import app.tasks.compile_schema as compile_mod
        with patch.object(compile_mod, "init_db_sync", noop_init_db), \
             patch.object(compile_mod, "SchemaCompiler", StubSchemaCompiler):
            await compile_mod._compile_schema_async(FakeTask(), tender_id)

        r = await http.get(f"/api/tenders/{tender_id}")
        check("tender → PENDING_APPROVAL", r.json()["status"] == "PENDING_APPROVAL")
        r = await http.get(f"/api/tenders/{tender_id}/schema")
        check("schema has 6 criteria", len(r.json()["criteria"]) == 6)
        schema_id = r.json()["schema_id"]

        print("\n== 3. Bidder upload gate & schema approval ==")
        with open(DATA_DIR / "bidder_a_typed.pdf", "rb") as f:
            r = await http.post(f"/api/tenders/{tender_id}/bidders",
                                data={"company_name": "Too Early Co"},
                                files=[("files", ("a.pdf", f, "application/pdf"))])
        check("bidder upload blocked before approval", r.status_code == 409)

        r = await http.patch(f"/api/tenders/{tender_id}/schema",
                             json={"action": "approve"})
        check("PATCH schema approve", r.status_code == 200)
        r = await http.get(f"/api/tenders/{tender_id}")
        check("tender → APPROVED", r.json()["status"] == "APPROVED")

        print("\n== 4. Bidder submissions (real files incl. scanned PDF + JPG) ==")
        bidder_files = {
            "Apex Constructions Pvt Ltd": ["bidder_a_typed.pdf"],
            "BuildRight Engineers": ["bidder_b_scanned.pdf"],
            "GreenForm Infrastructure": ["bidder_c_mixed.pdf", "bidder_c_cert_photo.jpg"],
        }
        bidder_ids = {}
        for company, names in bidder_files.items():
            files = [("files", (n, open(DATA_DIR / n, "rb"),
                                "application/octet-stream")) for n in names]
            r = await http.post(f"/api/tenders/{tender_id}/bidders",
                                data={"company_name": company}, files=files)
            check(f"POST bidder ({company})", r.status_code == 202, r.text)
            bidder_ids[company] = r.json()["bidder_id"]

        print("\n== 5. Extraction → rule engine → finalization pipeline ==")
        for company, bid in bidder_ids.items():
            await run_pipeline_for_bidder(bid, schema_id, company)
            r = await http.get(f"/api/tenders/{tender_id}/bidders")
            status = next(b["status"] for b in r.json() if b["bidder_id"] == bid)
            check(f"bidder EVALUATED ({company})", status == "EVALUATED")

        r = await http.get(f"/api/tenders/{tender_id}")
        check("tender → COMPLETE after all bidders", r.json()["status"] == "COMPLETE")

        print("\n== 6. Consolidated report ==")
        r = await http.get(f"/api/tenders/{tender_id}/report")
        check("GET report", r.status_code == 200)
        report = r.json()
        overall = {b["company_name"]: b["overall_verdict"]
                   for b in report["bidder_summaries"]}
        check("Apex overall PASS", overall["Apex Constructions Pvt Ltd"] == "PASS",
              str(overall))
        check("BuildRight overall FAIL (turnover & count below minimum)",
              overall["BuildRight Engineers"] == "FAIL")
        check("GreenForm overall REVIEW (low-confidence ISO date)",
              overall["GreenForm Infrastructure"] == "REVIEW")

        apex = next(b for b in report["bidder_summaries"]
                    if b["company_name"] == "Apex Constructions Pvt Ltd")
        cited = next(v for v in apex["criteria_verdicts"]
                     if v["criterion_id"] == "C-01")
        check("verdict carries citation (document, page, rule)",
              bool(cited["document_name"]) and cited["page_number"] is not None
              and bool(cited["rule_applied"]))

        print("\n== 7. Human review queue ==")
        r = await http.get(f"/api/tenders/{tender_id}/review")
        queue = r.json()
        check("review queue populated", len(queue) > 0, f"{len(queue)} items")
        check("mandatory items ranked first", queue[0]["mandatory"] is True)

        greenform_iso = next(i for i in queue
                             if i["company_name"] == "GreenForm Infrastructure"
                             and i["criterion_id"] == "C-04")
        r = await http.post(
            f"/api/tenders/{tender_id}/review/{greenform_iso['item_id']}",
            json={"action": "confirm", "verdict": "PASS",
                  "reason": "Certificate photo verified manually — valid until 2027."})
        check("officer resolves review item", r.status_code == 200)

        r = await http.get(f"/api/tenders/{tender_id}/report")
        gf = next(b for b in r.json()["bidder_summaries"]
                  if b["company_name"] == "GreenForm Infrastructure")
        check("GreenForm overall PASS after override", gf["overall_verdict"] == "PASS")
        c4 = next(v for v in gf["criteria_verdicts"] if v["criterion_id"] == "C-04")
        check("override recorded on verdict", c4["override_by"] == "officer")

        print("\n== 8. Audit trail integrity ==")
        from app.models.audit import AuditEntry
        count = await AuditEntry.find_all().count()
        check("audit entries written", count >= 25, f"{count} entries")
        check("hash chain verifies end-to-end",
              await AuditLogger().verify_chain() is True)

    print(f"\nSMOKE TEST PASSED — {len(PASSED)} checks OK")


if __name__ == "__main__":
    asyncio.run(main())
