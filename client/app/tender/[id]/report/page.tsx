"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import type { ConsolidatedReport, Tender } from "@/types";
import { api } from "@/lib/api";
import { TenderNav } from "@/components/TenderNav";
import { BidderVerdictCard } from "@/components/report/BidderVerdictCard";
import { ConsolidatedTable } from "@/components/report/ConsolidatedTable";

export default function ReportPage() {
  const { id } = useParams<{ id: string }>();
  const [tender, setTender] = useState<Tender | null>(null);
  const [report, setReport] = useState<ConsolidatedReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [t, r] = await Promise.all([api.getTender(id), api.getReport(id)]);
      setTender(t);
      setReport(r);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load report");
    }
  }, [id]);

  useEffect(() => {
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [load]);

  const reviewCount =
    report?.bidder_summaries.reduce(
      (acc, b) =>
        acc +
        b.criteria_verdicts.filter((v) => v.verdict === "REVIEW").length,
      0,
    ) ?? 0;

  return (
    <div>
      <TenderNav tender={tender} />
      {error && (
        <p className="mb-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-600">
          {error}
        </p>
      )}

      {report && report.bidder_summaries.length > 0 ? (
        <div className="space-y-6">
          {reviewCount > 0 && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
              {reviewCount} criterion verdict(s) need human review before this
              report is final.{" "}
              <Link
                href={`/tender/${id}/review`}
                className="font-semibold underline"
              >
                Open review queue
              </Link>
            </div>
          )}
          <section>
            <h2 className="mb-3 text-base font-semibold">
              Consolidated verdict matrix
            </h2>
            <ConsolidatedTable report={report} />
          </section>
          <section>
            <h2 className="mb-3 text-base font-semibold">
              Per-bidder detail (with citations)
            </h2>
            <div className="space-y-3">
              {report.bidder_summaries.map((b) => (
                <BidderVerdictCard key={b.bidder_id} summary={b} />
              ))}
            </div>
          </section>
        </div>
      ) : (
        !error && (
          <p className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-400">
            No evaluations yet — verdicts appear here as bidders are processed.
          </p>
        )
      )}
    </div>
  );
}
