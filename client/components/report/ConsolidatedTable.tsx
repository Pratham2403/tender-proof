"use client";

import type { ConsolidatedReport } from "@/types";
import { VerdictBadge } from "@/components/ui/badges";
import { Card } from "@/components/ui/primitives";

export function ConsolidatedTable({ report }: { report: ConsolidatedReport }) {
  if (report.bidder_summaries.length === 0) return null;
  const criteria = report.bidder_summaries[0].criteria_verdicts;

  return (
    <Card className="overflow-hidden">
      <div className="scrollbar-slim overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200/80 bg-slate-50/80 text-left">
              <th className="sticky left-0 z-10 bg-slate-50/95 px-5 py-3 text-[11px] font-semibold uppercase tracking-[0.1em] text-slate-400 backdrop-blur">
                Bidder
              </th>
              {criteria.map((c) => (
                <th
                  key={c.criterion_id}
                  className="px-3 py-3 text-center text-[11px] font-semibold uppercase tracking-[0.1em] text-slate-400"
                  title={`${c.label}${c.mandatory ? " (mandatory)" : " (optional)"}`}
                >
                  <span className="cursor-help underline decoration-dotted decoration-slate-300 underline-offset-4">
                    {c.criterion_id}
                  </span>
                  {!c.mandatory && (
                    <span className="ml-1 font-normal lowercase tracking-normal text-slate-300">
                      opt
                    </span>
                  )}
                </th>
              ))}
              <th className="px-5 py-3 text-center text-[11px] font-semibold uppercase tracking-[0.1em] text-slate-400">
                Overall
              </th>
            </tr>
          </thead>
          <tbody>
            {report.bidder_summaries.map((b) => (
              <tr
                key={b.bidder_id}
                className="border-b border-slate-100 transition-colors last:border-0 hover:bg-slate-50/60"
              >
                <td className="sticky left-0 z-10 max-w-56 truncate bg-white/95 px-5 py-3.5 font-medium text-slate-800 backdrop-blur">
                  {b.company_name}
                </td>
                {b.criteria_verdicts.map((v) => (
                  <td
                    key={v.criterion_id}
                    className="px-3 py-3.5 text-center"
                    title={`${v.label}: ${v.reason}`}
                  >
                    <VerdictBadge verdict={v.verdict} size="sm" />
                  </td>
                ))}
                <td className="px-5 py-3.5 text-center">
                  <VerdictBadge verdict={b.overall_verdict} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex flex-wrap items-center gap-x-5 gap-y-1 border-t border-slate-100 bg-slate-50/50 px-5 py-2.5 text-[11px] text-slate-400">
        <span>
          Overall = FAIL if any mandatory criterion fails · REVIEW if any
          awaits human judgment · PASS only when every mandatory criterion
          passes
        </span>
      </div>
    </Card>
  );
}
