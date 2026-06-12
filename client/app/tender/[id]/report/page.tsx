"use client";

import { useCallback, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import type { ConsolidatedReport, Tender, Verdict } from "@/types";
import { api } from "@/lib/api";
import { usePolling } from "@/lib/usePolling";
import { IconChevronRight, IconScale } from "@/components/ui/icons";
import {
  Alert,
  Card,
  EmptyState,
  ListSkeleton,
  SectionLabel,
} from "@/components/ui/primitives";
import { TenderNav } from "@/components/TenderNav";
import { BidderVerdictCard } from "@/components/report/BidderVerdictCard";
import { ConsolidatedTable } from "@/components/report/ConsolidatedTable";

function VerdictKpi({ label, value, tone }: {
  label: string;
  value: number;
  tone: string;
}) {
  return (
    <Card className="px-5 py-4">
      <p className="text-xs font-medium text-slate-400">{label}</p>
      <p className={`mt-1 text-2xl font-semibold tabular-nums tracking-tight ${tone}`}>
        {value}
      </p>
    </Card>
  );
}

export default function ReportPage() {
  const { id } = useParams<{ id: string }>();
  const [tender, setTender] = useState<Tender | null>(null);
  const [report, setReport] = useState<ConsolidatedReport | null>(null);

  const load = useCallback(async () => {
    const [t, r] = await Promise.all([api.getTender(id), api.getReport(id)]);
    setTender(t);
    setReport(r);
  }, [id]);

  usePolling(load, 5000);

  const overallCounts = (report?.bidder_summaries ?? []).reduce<
    Record<Verdict, number>
  >(
    (acc, b) => {
      acc[b.overall_verdict] += 1;
      return acc;
    },
    { PASS: 0, FAIL: 0, REVIEW: 0 },
  );

  const reviewCount =
    report?.bidder_summaries.reduce(
      (acc, b) =>
        acc + b.criteria_verdicts.filter((v) => v.verdict === "REVIEW").length,
      0,
    ) ?? 0;

  return (
    <div className="animate-fade-up">
      <TenderNav tender={tender} />

      {!report && <ListSkeleton rows={3} />}

      {report && report.bidder_summaries.length === 0 && (
        <EmptyState
          icon={<IconScale className="h-5 w-5" />}
          title="No evaluations yet"
          description="Verdicts appear here in real time as bidder documents are extracted and judged by the rule engine."
          action={
            <Link
              href={`/tender/${id}/bidders`}
              className="text-sm font-medium text-indigo-600 hover:text-indigo-700"
            >
              Upload bidders →
            </Link>
          }
        />
      )}

      {report && report.bidder_summaries.length > 0 && (
        <div className="space-y-8">
          {reviewCount > 0 && (
            <Alert tone="warning">
              <span className="font-semibold">{reviewCount}</span> criterion
              verdict{reviewCount === 1 ? "" : "s"} need human review before
              this report is final.{" "}
              <Link
                href={`/tender/${id}/review`}
                className="inline-flex items-center gap-0.5 font-semibold underline underline-offset-2 hover:text-amber-900"
              >
                Open review queue
                <IconChevronRight className="h-3.5 w-3.5" />
              </Link>
            </Alert>
          )}

          <div className="grid grid-cols-3 gap-3">
            <VerdictKpi label="Bidders eligible" value={overallCounts.PASS} tone="text-emerald-600" />
            <VerdictKpi label="Bidders ineligible" value={overallCounts.FAIL} tone="text-rose-600" />
            <VerdictKpi label="Pending review" value={overallCounts.REVIEW} tone="text-amber-600" />
          </div>

          <section>
            <div className="mb-3">
              <SectionLabel>Verdict matrix</SectionLabel>
            </div>
            <ConsolidatedTable report={report} />
          </section>

          <section>
            <div className="mb-3">
              <SectionLabel>Per-bidder detail with citations</SectionLabel>
            </div>
            <div className="space-y-3">
              {report.bidder_summaries.map((b) => (
                <BidderVerdictCard key={b.bidder_id} summary={b} />
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
