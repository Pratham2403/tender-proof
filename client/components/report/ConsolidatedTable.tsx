"use client";

import type { ConsolidatedReport } from "@/types";
import { VerdictBadge } from "@/components/ui/badges";

export function ConsolidatedTable({ report }: { report: ConsolidatedReport }) {
  if (report.bidder_summaries.length === 0) return null;
  const criteria = report.bidder_summaries[0].criteria_verdicts;

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
            <th className="px-4 py-3 font-medium">Bidder</th>
            {criteria.map((c) => (
              <th
                key={c.criterion_id}
                className="px-3 py-3 text-center font-medium"
                title={c.label}
              >
                {c.criterion_id}
                {c.mandatory ? "" : " (opt)"}
              </th>
            ))}
            <th className="px-4 py-3 text-center font-medium">Overall</th>
          </tr>
        </thead>
        <tbody>
          {report.bidder_summaries.map((b) => (
            <tr key={b.bidder_id} className="border-b border-slate-100 last:border-0">
              <td className="px-4 py-3 font-medium">{b.company_name}</td>
              {b.criteria_verdicts.map((v) => (
                <td key={v.criterion_id} className="px-3 py-3 text-center">
                  <VerdictBadge verdict={v.verdict} />
                </td>
              ))}
              <td className="px-4 py-3 text-center">
                <VerdictBadge verdict={b.overall_verdict} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
