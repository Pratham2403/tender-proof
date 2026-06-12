"use client";

import { useState } from "react";
import type { BidderSummary } from "@/types";
import { ConfidenceBar, VerdictBadge } from "@/components/ui/badges";

export function BidderVerdictCard({ summary }: { summary: BidderSummary }) {
  const [open, setOpen] = useState(false);
  const counts = summary.criteria_verdicts.reduce(
    (acc, v) => ({ ...acc, [v.verdict]: (acc[v.verdict] ?? 0) + 1 }),
    {} as Record<string, number>,
  );

  return (
    <div className="rounded-xl border border-slate-200 bg-white">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between gap-3 p-4 text-left"
      >
        <div className="flex items-center gap-3">
          <VerdictBadge verdict={summary.overall_verdict} />
          <span className="text-sm font-semibold">{summary.company_name}</span>
        </div>
        <div className="flex items-center gap-3 text-xs text-slate-500">
          <span>
            {counts.PASS ?? 0} pass · {counts.FAIL ?? 0} fail ·{" "}
            {counts.REVIEW ?? 0} review
          </span>
          <span
            className={`transition-transform ${open ? "rotate-180" : ""}`}
          >
            ▾
          </span>
        </div>
      </button>
      {open && (
        <div className="border-t border-slate-100 p-4">
          <ul className="space-y-3">
            {summary.criteria_verdicts.map((v) => (
              <li
                key={v.criterion_id}
                className="rounded-lg border border-slate-100 bg-slate-50 p-3"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-slate-500">
                      {v.criterion_id}
                    </span>
                    <span className="text-sm font-medium">{v.label}</span>
                    {v.mandatory && (
                      <span className="rounded bg-indigo-50 px-1.5 text-[10px] font-medium text-indigo-600">
                        MANDATORY
                      </span>
                    )}
                    {v.override_by && (
                      <span className="rounded bg-purple-50 px-1.5 text-[10px] font-medium text-purple-600">
                        OFFICER OVERRIDE
                      </span>
                    )}
                  </div>
                  <VerdictBadge verdict={v.verdict} />
                </div>
                <p className="mt-1.5 text-xs text-slate-600">{v.reason}</p>
                <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
                  {v.extracted_value != null && (
                    <span>
                      Value:{" "}
                      <code className="rounded bg-white px-1">
                        {v.extracted_value}
                      </code>
                    </span>
                  )}
                  {v.document_name && (
                    <span>
                      Source: {v.document_name}
                      {v.page_number ? `, p.${v.page_number}` : ""}
                    </span>
                  )}
                  {v.rule_applied && <span>Rule: {v.rule_applied}</span>}
                  <ConfidenceBar confidence={v.confidence} />
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
