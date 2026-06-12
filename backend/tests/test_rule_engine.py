"""
RuleEngine is the highest-priority unit test target — pure functions, no mocks
needed, and correctness here is the system's legal guarantee. Every criterion
type gets pass / fail / review cases, plus edge cases: value at exact
threshold, value = None, confidence = exactly 0.70.
"""

from datetime import datetime

import pytest

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
from app.models.verdict import Verdict
from app.services.rule_engine import CONFIDENCE_THRESHOLD, RuleEngine

IDS = dict(bidder_id="b1", tender_id="t1", schema_id="s1")


def make_extraction(value, confidence=0.95, **kw):
    return CriterionExtraction(
        criterion_id="C-01", extracted_value=value, confidence=confidence,
        document_name=kw.get("document_name", "doc.pdf"),
        page_number=kw.get("page_number", 1),
        raw_text=kw.get("raw_text", "raw"),
    )


def currency_criterion(minimum=5.0, mandatory=True):
    return Criterion(
        criterion_id="C-01", label="Annual Turnover Minimum",
        criterion_type=CriterionType.CURRENCY_THRESHOLD, mandatory=mandatory,
        params=CurrencyThresholdParams(minimum_crore=minimum),
        accepted_evidence=["audited balance sheet"], source_text="...",
    )


def count_criterion(minimum=3, within_years=5):
    return Criterion(
        criterion_id="C-01", label="Similar Projects",
        criterion_type=CriterionType.COUNT_MINIMUM, mandatory=True,
        params=CountMinimumParams(minimum_count=minimum, within_years=within_years),
        accepted_evidence=[], source_text="...",
    )


def boolean_criterion(accepted=None):
    return Criterion(
        criterion_id="C-01", label="GST Registration",
        criterion_type=CriterionType.BOOLEAN_PRESENCE, mandatory=True,
        params=BooleanPresenceParams(accepted_values=accepted or []),
        accepted_evidence=[], source_text="...",
    )


def date_criterion(not_expired="2025-03-31T00:00:00"):
    return Criterion(
        criterion_id="C-01", label="ISO 9001 Validity",
        criterion_type=CriterionType.DATE_RANGE, mandatory=True,
        params=DateRangeParams(not_expired_as_of=datetime.fromisoformat(not_expired)),
        accepted_evidence=[], source_text="...",
    )


def similarity_criterion():
    return Criterion(
        criterion_id="C-01", label="Similar Project Experience",
        criterion_type=CriterionType.SIMILARITY_SCORE, mandatory=True,
        params=SimilarityScoreParams(description="similar construction projects"),
        accepted_evidence=[], source_text="...",
    )


engine = RuleEngine()


class TestConfidenceGates:
    def test_no_extraction_routes_to_review(self):
        v = engine.evaluate_criterion(currency_criterion(), None, **IDS)
        assert v.verdict == Verdict.REVIEW
        assert "not found" in v.rule_applied

    def test_none_value_routes_to_review(self):
        v = engine.evaluate_criterion(currency_criterion(), make_extraction(None), **IDS)
        assert v.verdict == Verdict.REVIEW

    def test_low_confidence_routes_to_review_even_when_rule_would_fail(self):
        # Silent disqualification prevention: a failing value with low
        # confidence must produce REVIEW, never FAIL.
        v = engine.evaluate_criterion(
            currency_criterion(minimum=5.0), make_extraction("2.0", confidence=0.50), **IDS)
        assert v.verdict == Verdict.REVIEW

    def test_confidence_exactly_at_threshold_applies_rule(self):
        v = engine.evaluate_criterion(
            currency_criterion(minimum=5.0),
            make_extraction("8.0", confidence=CONFIDENCE_THRESHOLD), **IDS)
        assert v.verdict == Verdict.PASS

    def test_confidence_just_below_threshold_routes_to_review(self):
        v = engine.evaluate_criterion(
            currency_criterion(minimum=5.0),
            make_extraction("8.0", confidence=CONFIDENCE_THRESHOLD - 0.01), **IDS)
        assert v.verdict == Verdict.REVIEW


class TestCurrencyThreshold:
    def test_pass_above_threshold(self):
        v = engine.evaluate_criterion(currency_criterion(5.0), make_extraction("8.45"), **IDS)
        assert v.verdict == Verdict.PASS

    def test_fail_below_threshold(self):
        v = engine.evaluate_criterion(currency_criterion(5.0), make_extraction("3.20"), **IDS)
        assert v.verdict == Verdict.FAIL

    def test_pass_at_exact_threshold(self):
        v = engine.evaluate_criterion(currency_criterion(5.0), make_extraction("5.0"), **IDS)
        assert v.verdict == Verdict.PASS

    def test_parses_formatted_currency(self):
        v = engine.evaluate_criterion(currency_criterion(5.0), make_extraction("₹8,45 Cr".replace(",", ".")), **IDS)
        assert v.verdict == Verdict.PASS

    def test_unparseable_value_routes_to_review(self):
        v = engine.evaluate_criterion(currency_criterion(5.0), make_extraction("eight crore"), **IDS)
        assert v.verdict == Verdict.REVIEW
        assert v.rule_applied == "value parse error"


class TestCountMinimum:
    def test_pass(self):
        v = engine.evaluate_criterion(count_criterion(3), make_extraction("5"), **IDS)
        assert v.verdict == Verdict.PASS

    def test_fail(self):
        v = engine.evaluate_criterion(count_criterion(3), make_extraction("2"), **IDS)
        assert v.verdict == Verdict.FAIL

    def test_pass_at_exact_minimum(self):
        v = engine.evaluate_criterion(count_criterion(3), make_extraction("3"), **IDS)
        assert v.verdict == Verdict.PASS

    def test_unparseable_routes_to_review(self):
        v = engine.evaluate_criterion(count_criterion(3), make_extraction("several"), **IDS)
        assert v.verdict == Verdict.REVIEW


class TestBooleanPresence:
    def test_pass_with_accepted_value_match(self):
        v = engine.evaluate_criterion(
            boolean_criterion(["GST", "GSTIN"]),
            make_extraction("GSTIN 27AAACA1234F1Z5"), **IDS)
        assert v.verdict == Verdict.PASS

    def test_match_is_case_insensitive(self):
        v = engine.evaluate_criterion(
            boolean_criterion(["gstin"]), make_extraction("GSTIN 27AAACA1234F1Z5"), **IDS)
        assert v.verdict == Verdict.PASS

    def test_fail_without_match(self):
        v = engine.evaluate_criterion(
            boolean_criterion(["GST", "GSTIN"]), make_extraction("PAN ABCDE1234F"), **IDS)
        assert v.verdict == Verdict.FAIL

    def test_any_nonempty_passes_when_no_accepted_values(self):
        v = engine.evaluate_criterion(boolean_criterion([]), make_extraction("present"), **IDS)
        assert v.verdict == Verdict.PASS

    def test_whitespace_only_fails_when_no_accepted_values(self):
        v = engine.evaluate_criterion(boolean_criterion([]), make_extraction("   "), **IDS)
        assert v.verdict == Verdict.FAIL


class TestDateRange:
    def test_pass_unexpired(self):
        v = engine.evaluate_criterion(date_criterion("2025-03-31T00:00:00"),
                                      make_extraction("2026-08-14"), **IDS)
        assert v.verdict == Verdict.PASS

    def test_fail_expired(self):
        v = engine.evaluate_criterion(date_criterion("2025-03-31T00:00:00"),
                                      make_extraction("2024-11-30"), **IDS)
        assert v.verdict == Verdict.FAIL

    def test_unparseable_date_routes_to_review(self):
        v = engine.evaluate_criterion(date_criterion(), make_extraction("next year"), **IDS)
        assert v.verdict == Verdict.REVIEW


class TestSimilarityScore:
    def test_pass_at_or_above_pass_threshold(self):
        v = engine.evaluate_criterion(similarity_criterion(), make_extraction("0.85"), **IDS)
        assert v.verdict == Verdict.PASS
        v = engine.evaluate_criterion(similarity_criterion(), make_extraction("0.7"), **IDS)
        assert v.verdict == Verdict.PASS

    def test_fail_at_or_below_fail_threshold(self):
        v = engine.evaluate_criterion(similarity_criterion(), make_extraction("0.2"), **IDS)
        assert v.verdict == Verdict.FAIL
        v = engine.evaluate_criterion(similarity_criterion(), make_extraction("0.4"), **IDS)
        assert v.verdict == Verdict.FAIL

    def test_review_between_thresholds(self):
        v = engine.evaluate_criterion(similarity_criterion(), make_extraction("0.55"), **IDS)
        assert v.verdict == Verdict.REVIEW


class TestDeterminism:
    def test_same_input_same_output(self):
        c, e = currency_criterion(5.0), make_extraction("8.45", confidence=0.9)
        first = engine.evaluate_criterion(c, e, **IDS)
        for _ in range(10):
            again = engine.evaluate_criterion(c, e, **IDS)
            assert again.verdict == first.verdict
            assert again.rule_applied == first.rule_applied
            assert again.reason == first.reason


class TestVerdictCitations:
    def test_verdict_carries_full_citation_trail(self):
        e = make_extraction("8.45", document_name="balance_sheet.pdf",
                            page_number=3, raw_text="Turnover: 8.45 Cr")
        v = engine.evaluate_criterion(currency_criterion(5.0), e, **IDS)
        assert v.criterion_id == "C-01"
        assert v.document_name == "balance_sheet.pdf"
        assert v.page_number == 3
        assert v.raw_text == "Turnover: 8.45 Cr"
        assert v.extracted_value == "8.45"
        assert v.rule_applied
        assert v.reason
