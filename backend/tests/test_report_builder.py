import pytest

from app.models.bidder import Bidder
from app.models.tender import (
    BooleanPresenceParams,
    Criterion,
    CriterionType,
    CurrencyThresholdParams,
    EvaluationSchema,
)
from app.models.verdict import Verdict, VerdictRecord
from app.services.report_builder import ReportBuilder


def make_schema(tender_id: str) -> EvaluationSchema:
    return EvaluationSchema(
        tender_id=tender_id,
        criteria=[
            Criterion(criterion_id="C-01", label="Turnover",
                      criterion_type=CriterionType.CURRENCY_THRESHOLD, mandatory=True,
                      params=CurrencyThresholdParams(minimum_crore=5.0),
                      accepted_evidence=[], source_text=""),
            Criterion(criterion_id="C-02", label="GST",
                      criterion_type=CriterionType.BOOLEAN_PRESENCE, mandatory=True,
                      params=BooleanPresenceParams(accepted_values=["GST"]),
                      accepted_evidence=[], source_text=""),
            Criterion(criterion_id="C-03", label="MSME (optional)",
                      criterion_type=CriterionType.BOOLEAN_PRESENCE, mandatory=False,
                      params=BooleanPresenceParams(), accepted_evidence=[], source_text=""),
        ],
    )


async def add_verdict(bidder_id, criterion_id, verdict):
    await VerdictRecord(
        bidder_id=bidder_id, tender_id="t1", schema_id="s1",
        criterion_id=criterion_id, verdict=verdict,
        extracted_value="x", document_name="d.pdf", page_number=1, raw_text="r",
        rule_applied="rule", reason="reason", confidence=0.9,
    ).insert()


@pytest.mark.asyncio
async def test_overall_pass_requires_all_mandatory_pass(db):
    bidder = Bidder(tender_id="t1", company_name="Apex", file_paths=[])
    await bidder.insert()
    bid = str(bidder.id)
    await add_verdict(bid, "C-01", Verdict.PASS)
    await add_verdict(bid, "C-02", Verdict.PASS)
    await add_verdict(bid, "C-03", Verdict.FAIL)  # optional — must not affect overall

    report = await ReportBuilder().build("t1", make_schema("t1"))
    assert report.bidder_summaries[0].overall_verdict == Verdict.PASS


@pytest.mark.asyncio
async def test_overall_fail_when_any_mandatory_fails(db):
    bidder = Bidder(tender_id="t1", company_name="BuildRight", file_paths=[])
    await bidder.insert()
    bid = str(bidder.id)
    await add_verdict(bid, "C-01", Verdict.FAIL)
    await add_verdict(bid, "C-02", Verdict.PASS)

    report = await ReportBuilder().build("t1", make_schema("t1"))
    assert report.bidder_summaries[0].overall_verdict == Verdict.FAIL


@pytest.mark.asyncio
async def test_overall_review_when_mandatory_in_review(db):
    bidder = Bidder(tender_id="t1", company_name="GreenForm", file_paths=[])
    await bidder.insert()
    bid = str(bidder.id)
    await add_verdict(bid, "C-01", Verdict.PASS)
    await add_verdict(bid, "C-02", Verdict.REVIEW)

    report = await ReportBuilder().build("t1", make_schema("t1"))
    assert report.bidder_summaries[0].overall_verdict == Verdict.REVIEW


@pytest.mark.asyncio
async def test_missing_mandatory_verdict_means_review(db):
    bidder = Bidder(tender_id="t1", company_name="Apex", file_paths=[])
    await bidder.insert()
    await add_verdict(str(bidder.id), "C-01", Verdict.PASS)
    # C-02 never evaluated

    report = await ReportBuilder().build("t1", make_schema("t1"))
    summary = report.bidder_summaries[0]
    assert summary.overall_verdict == Verdict.REVIEW
    c2 = next(c for c in summary.criteria_verdicts if c.criterion_id == "C-02")
    assert c2.verdict == Verdict.REVIEW
    assert c2.reason == "Not evaluated"
