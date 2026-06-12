"use client";

import { useState } from "react";
import type { BidderSummary } from "@/types";
import { ConfidenceBar, VerdictBadge } from "@/components/ui/badges";
import { IconChevronDown, IconDocument } from "@/components/ui/icons";
import { Card } from "@/components/ui/primitives";

export function BidderVerdictCard({ summary }: { summary: BidderSummary }) {
  const [open, setOpen] = useState(false);
  const counts = summary.criteria_verdicts.reduce<Record<string, number>>(
    (acc, v) => {
      acc[v.verdict] = (acc[v.verdict] ?? 0) + 1;
      return acc;
    },
    {},
  );

  return (
    <Card className="overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left transition-colors hover:bg-slate-50/60"
      >
        <div className="flex min-w-0 items-center gap-3">
          <VerdictBadge verdict={summary.overall_verdict} />
          <span className="truncate text-sm font-semibold text-slate-900">
            {summary.company_name}
          </span>
        </div>
        <div className="flex shrink-0 items-center gap-4">
          <span className="hidden gap-3 text-xs tabular-nums text-slate-400 sm:flex">
            <span className="text-emerald-600">{counts.PASS ?? 0} pass</span>
            <span className="text-rose-600">{counts.FAIL ?? 0} fail</span>
            <span className="text-amber-600">{counts.REVIEW ?? 0} review</span>
          </span>
          <IconChevronDown
            className={`h-4 w-4 text-slate-400 transition-transform duration-200 ${open ? "rotate-180" : ""}`}
          />
        </div>
      </button>

      {open && (
        <div className="border-t border-slate-100">
          <ul className="divide-y divide-slate-100">
            {summary.criteria_verdicts.map((v) => (
              <li key={v.criterion_id} className="px-5 py-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-[11px] font-medium text-slate-400">
                        {v.criterion_id}
                      </span>
                      <span className="text-sm font-semibold text-slate-800">
                        {v.label}
                      </span>
                      {v.mandatory && (
                        <span className="rounded-full bg-indigo-50 px-2 py-px text-[10px] font-semibold text-indigo-600 ring-1 ring-inset ring-indigo-600/20">
                          MANDATORY
                        </span>
                      )}
                      {v.override_by && (
                        <span className="rounded-full bg-purple-50 px-2 py-px text-[10px] font-semibold text-purple-600 ring-1 ring-inset ring-purple-600/20">
                          OFFICER OVERRIDE
                        </span>
                      )}
                    </div>
                    <p className="mt-1.5 text-sm leading-relaxed text-slate-600">
                      {v.reason}
                    </p>
                  </div>
                  <VerdictBadge verdict={v.verdict} />
                </div>

                <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-slate-500">
                  {v.extracted_value != null && (
                    <span>
                      Value:{" "}
                      <code className="rounded-md bg-slate-100 px-1.5 py-0.5 font-mono text-slate-700">
                        {v.extracted_value}
                      </code>
                    </span>
                  )}
                  {v.document_name && (
                    <span className="inline-flex items-center gap-1.5">
                      <IconDocument className="h-3.5 w-3.5 text-slate-400" />
                      {v.document_name}
                      {v.page_number ? `, p.${v.page_number}` : ""}
                    </span>
                  )}
                  {v.rule_applied && (
                    <span>
                      Rule:{" "}
                      <code className="rounded-md bg-slate-100 px-1.5 py-0.5 font-mono text-slate-700">
                        {v.rule_applied}
                      </code>
                    </span>
                  )}
                  <ConfidenceBar confidence={v.confidence} />
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}
