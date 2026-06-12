from app.models.bidder import Bidder
from app.models.tender import EvaluationSchema
from app.models.verdict import Verdict, VerdictRecord
from app.schemas.verdict import BidderSummary, ConsolidatedReport, CriterionVerdict


class ReportBuilder:
    """
    Assembles ConsolidatedReport from persisted VerdictRecords.
    Read-only — no writes. Pure transformation.
    """

    async def build(self, tender_id: str, schema: EvaluationSchema) -> ConsolidatedReport:
        bidders = await Bidder.find(Bidder.tender_id == tender_id).to_list()
        summaries: list[BidderSummary] = []

        for bidder in bidders:
            verdicts = await VerdictRecord.find(
                VerdictRecord.bidder_id == str(bidder.id)
            ).to_list()

            verdict_map = {v.criterion_id: v for v in verdicts}
            overall = self._compute_overall(verdicts, schema)

            criteria_verdicts = []
            for c in schema.criteria:
                v = verdict_map.get(c.criterion_id)
                criteria_verdicts.append(CriterionVerdict(
                    criterion_id=c.criterion_id,
                    label=c.label,
                    mandatory=c.mandatory,
                    verdict=v.verdict if v else Verdict.REVIEW,
                    extracted_value=v.extracted_value if v else None,
                    document_name=v.document_name if v else None,
                    page_number=v.page_number if v else None,
                    reason=v.reason if v else "Not evaluated",
                    confidence=v.confidence if v else 0.0,
                    rule_applied=v.rule_applied if v else None,
                    override_by=v.override_by if v else None,
                ))

            summaries.append(BidderSummary(
                bidder_id=str(bidder.id),
                company_name=bidder.company_name,
                overall_verdict=overall,
                criteria_verdicts=criteria_verdicts,
            ))

        return ConsolidatedReport(tender_id=tender_id, bidder_summaries=summaries)

    def _compute_overall(self, verdicts: list[VerdictRecord], schema: EvaluationSchema) -> Verdict:
        """
        Overall = FAIL if any mandatory criterion is FAIL.
        Overall = REVIEW if any mandatory criterion is REVIEW (or missing).
        Overall = PASS only if all mandatory criteria are PASS.
        """
        mandatory_ids = {c.criterion_id for c in schema.criteria if c.mandatory}
        verdict_map = {v.criterion_id: v for v in verdicts}

        if any(cid in verdict_map and verdict_map[cid].verdict == Verdict.FAIL
               for cid in mandatory_ids):
            return Verdict.FAIL
        if any(cid not in verdict_map or verdict_map[cid].verdict == Verdict.REVIEW
               for cid in mandatory_ids):
            return Verdict.REVIEW
        return Verdict.PASS
