from datetime import datetime

from app.config import settings
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
from app.models.verdict import Verdict, VerdictRecord
from app.services.value_parsing import parse_count, parse_crore, parse_score

CONFIDENCE_THRESHOLD = settings.confidence_threshold  # Extractions below this → REVIEW


class RuleEngine:
    """
    Pure deterministic verdict computation. Zero LLM calls.
    Same input always produces same output.
    """

    def evaluate_criterion(
        self,
        criterion: Criterion,
        extraction: CriterionExtraction | None,
        bidder_id: str,
        tender_id: str,
        schema_id: str,
    ) -> VerdictRecord:
        """
        Single criterion evaluation entry point.
        Returns a VerdictRecord. Never raises — all error states become REVIEW.
        """
        # Gate 1: no extraction found at all
        if extraction is None or extraction.extracted_value is None:
            return self._make_verdict(
                criterion, extraction, bidder_id, tender_id, schema_id,
                verdict=Verdict.REVIEW,
                rule_applied="value not found in any document page",
                reason="No value matching this criterion was extracted from the bidder's documents.",
                confidence=0.0,
            )

        # Gate 2: confidence below threshold
        if extraction.confidence < CONFIDENCE_THRESHOLD:
            return self._make_verdict(
                criterion, extraction, bidder_id, tender_id, schema_id,
                verdict=Verdict.REVIEW,
                rule_applied=f"confidence {extraction.confidence:.2f} < threshold {CONFIDENCE_THRESHOLD}",
                reason=f"Extraction confidence ({extraction.confidence:.0%}) is below the required threshold. "
                       f"Human review required to confirm the value.",
                confidence=extraction.confidence,
            )

        # Gate 3: apply typed rule
        return self._apply_typed_rule(criterion, extraction, bidder_id, tender_id, schema_id)

    def _apply_typed_rule(
        self,
        criterion: Criterion,
        extraction: CriterionExtraction,
        bidder_id: str,
        tender_id: str,
        schema_id: str,
    ) -> VerdictRecord:
        t = criterion.criterion_type
        p = criterion.params
        v = extraction.extracted_value
        ids = (bidder_id, tender_id, schema_id)

        try:
            if t == CriterionType.CURRENCY_THRESHOLD:
                return self._eval_currency(criterion, extraction, p, v, *ids)
            elif t == CriterionType.COUNT_MINIMUM:
                return self._eval_count(criterion, extraction, p, v, *ids)
            elif t == CriterionType.BOOLEAN_PRESENCE:
                return self._eval_boolean(criterion, extraction, p, v, *ids)
            elif t == CriterionType.DATE_RANGE:
                return self._eval_date(criterion, extraction, p, v, *ids)
            elif t == CriterionType.SIMILARITY_SCORE:
                return self._eval_similarity(criterion, extraction, p, v, *ids)
            raise ValueError(f"Unknown criterion type: {t}")
        except Exception as e:
            return self._make_verdict(
                criterion, extraction, bidder_id, tender_id, schema_id,
                verdict=Verdict.REVIEW,
                rule_applied="value parse error",
                reason=f"Could not parse extracted value '{v}' for rule evaluation: {e}",
                confidence=extraction.confidence,
            )

    def _eval_currency(self, criterion, extraction, p: CurrencyThresholdParams, v, *ids) -> VerdictRecord:
        amount = parse_crore(v)
        passed = amount >= p.minimum_crore
        rule = f"turnover {amount:.2f} Cr {'≥' if passed else '<'} {p.minimum_crore} Cr"
        reason = (f"Annual turnover of ₹{amount:.2f} Cr meets the minimum of ₹{p.minimum_crore} Cr."
                  if passed else
                  f"Annual turnover of ₹{amount:.2f} Cr is below the minimum of ₹{p.minimum_crore} Cr.")
        return self._make_verdict(criterion, extraction, *ids,
                                  verdict=Verdict.PASS if passed else Verdict.FAIL,
                                  rule_applied=rule, reason=reason,
                                  confidence=extraction.confidence)

    def _eval_count(self, criterion, extraction, p: CountMinimumParams, v, *ids) -> VerdictRecord:
        count = parse_count(v)
        passed = count >= p.minimum_count
        qualifier = f" (within last {p.within_years} years)" if p.within_years else ""
        rule = f"count {count} {'≥' if passed else '<'} {p.minimum_count}{qualifier}"
        reason = (f"Declared {count} similar project(s){qualifier}, meeting the minimum of {p.minimum_count}."
                  if passed else
                  f"Declared {count} similar project(s){qualifier}, below the minimum of {p.minimum_count}.")
        return self._make_verdict(criterion, extraction, *ids,
                                  verdict=Verdict.PASS if passed else Verdict.FAIL,
                                  rule_applied=rule, reason=reason,
                                  confidence=extraction.confidence)

    def _eval_boolean(self, criterion, extraction, p: BooleanPresenceParams, v, *ids) -> VerdictRecord:
        # If accepted_values list given, v must contain one of them; else any non-empty value passes
        if p.accepted_values:
            passed = any(av.lower() in v.lower() for av in p.accepted_values)
        else:
            passed = bool(v and v.strip())
        rule = f"'{v}' {'matches' if passed else 'does not match'} accepted values {p.accepted_values or ['any']}"
        reason = (f"Valid certification/registration found: '{v}'."
                  if passed else
                  f"No valid certification/registration found. Expected one of: {p.accepted_values}.")
        return self._make_verdict(criterion, extraction, *ids,
                                  verdict=Verdict.PASS if passed else Verdict.FAIL,
                                  rule_applied=rule, reason=reason,
                                  confidence=extraction.confidence)

    def _eval_date(self, criterion, extraction, p: DateRangeParams, v, *ids) -> VerdictRecord:
        extracted_date = datetime.fromisoformat(v.strip())
        if p.not_expired_as_of and extracted_date < p.not_expired_as_of:
            rule = f"expiry {v} < required {p.not_expired_as_of.date()}"
            reason = f"Document expired on {v}, before required date {p.not_expired_as_of.date()}."
            return self._make_verdict(criterion, extraction, *ids,
                                      verdict=Verdict.FAIL, rule_applied=rule,
                                      reason=reason, confidence=extraction.confidence)
        if p.issued_after and extracted_date < p.issued_after:
            rule = f"issue date {v} < required {p.issued_after.date()}"
            reason = f"Document issued on {v}, before required date {p.issued_after.date()}."
            return self._make_verdict(criterion, extraction, *ids,
                                      verdict=Verdict.FAIL, rule_applied=rule,
                                      reason=reason, confidence=extraction.confidence)
        rule = f"date {v} within valid range"
        reason = f"Document date {v} satisfies the required date range."
        return self._make_verdict(criterion, extraction, *ids,
                                  verdict=Verdict.PASS, rule_applied=rule,
                                  reason=reason, confidence=extraction.confidence)

    def _eval_similarity(self, criterion, extraction, p: SimilarityScoreParams, v, *ids) -> VerdictRecord:
        score = parse_score(v)  # v is the LLM-produced similarity score string
        if score >= p.pass_threshold:
            verdict, reason = Verdict.PASS, f"Similarity score {score:.2f} ≥ pass threshold {p.pass_threshold}."
        elif score <= p.fail_threshold:
            verdict, reason = Verdict.FAIL, f"Similarity score {score:.2f} ≤ fail threshold {p.fail_threshold}."
        else:
            verdict, reason = Verdict.REVIEW, (
                f"Similarity score {score:.2f} is between fail ({p.fail_threshold}) "
                f"and pass ({p.pass_threshold}) thresholds. Human judgment required."
            )
        rule = f"similarity score {score:.2f} evaluated against [{p.fail_threshold}, {p.pass_threshold}]"
        return self._make_verdict(criterion, extraction, *ids,
                                  verdict=verdict, rule_applied=rule,
                                  reason=reason, confidence=extraction.confidence)

    def _make_verdict(
        self, criterion: Criterion, extraction: CriterionExtraction | None,
        bidder_id: str, tender_id: str, schema_id: str,
        verdict: Verdict, rule_applied: str, reason: str, confidence: float,
    ) -> VerdictRecord:
        return VerdictRecord(
            bidder_id=bidder_id,
            tender_id=tender_id,
            schema_id=schema_id,
            criterion_id=criterion.criterion_id,
            verdict=verdict,
            extracted_value=extraction.extracted_value if extraction else None,
            document_name=extraction.document_name if extraction else None,
            page_number=extraction.page_number if extraction else None,
            raw_text=extraction.raw_text if extraction else None,
            rule_applied=rule_applied,
            reason=reason,
            confidence=confidence,
        )
