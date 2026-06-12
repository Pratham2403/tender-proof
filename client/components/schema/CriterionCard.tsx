"use client";

import type { Criterion } from "@/types";

const TYPE_LABELS: Record<string, string> = {
  CurrencyThreshold: "Currency threshold",
  CountMinimum: "Count minimum",
  BooleanPresence: "Presence check",
  DateRange: "Date range",
  SimilarityScore: "Similarity score",
};

function describeParams(c: Criterion): string {
  const p = c.params as Record<string, unknown>;
  switch (c.criterion_type) {
    case "CurrencyThreshold":
      return `≥ ₹${p.minimum_crore} Cr (${p.currency ?? "INR"})`;
    case "CountMinimum":
      return `≥ ${p.minimum_count}${p.within_years ? ` within last ${p.within_years} years` : ""}`;
    case "BooleanPresence": {
      const vals = (p.accepted_values as string[]) ?? [];
      return vals.length ? `must contain: ${vals.join(" / ")}` : "must be present";
    }
    case "DateRange":
      return [
        p.not_expired_as_of
          ? `not expired as of ${String(p.not_expired_as_of).slice(0, 10)}`
          : null,
        p.issued_after
          ? `issued after ${String(p.issued_after).slice(0, 10)}`
          : null,
      ]
        .filter(Boolean)
        .join(", ") || "any valid date";
    case "SimilarityScore":
      return `pass ≥ ${p.pass_threshold ?? 0.7}, fail ≤ ${p.fail_threshold ?? 0.4}`;
    default:
      return "";
  }
}

export function CriterionCard({
  criterion,
  editable,
  onToggleMandatory,
  onRemove,
}: {
  criterion: Criterion;
  editable?: boolean;
  onToggleMandatory?: () => void;
  onRemove?: () => void;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="rounded bg-slate-100 px-2 py-0.5 font-mono text-xs text-slate-600">
            {criterion.criterion_id}
          </span>
          <h3 className="text-sm font-semibold">{criterion.label}</h3>
        </div>
        <div className="flex items-center gap-2">
          {editable ? (
            <button
              type="button"
              onClick={onToggleMandatory}
              className={`rounded-full px-2.5 py-0.5 text-xs font-medium transition ${
                criterion.mandatory
                  ? "bg-indigo-100 text-indigo-700 hover:bg-indigo-200"
                  : "bg-slate-100 text-slate-500 hover:bg-slate-200"
              }`}
              title="Toggle mandatory"
            >
              {criterion.mandatory ? "Mandatory" : "Optional"}
            </button>
          ) : (
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                criterion.mandatory
                  ? "bg-indigo-100 text-indigo-700"
                  : "bg-slate-100 text-slate-500"
              }`}
            >
              {criterion.mandatory ? "Mandatory" : "Optional"}
            </span>
          )}
          {editable && (
            <button
              type="button"
              onClick={onRemove}
              className="rounded-full px-2 py-0.5 text-xs text-rose-500 hover:bg-rose-50"
              title="Remove criterion"
            >
              ✕
            </button>
          )}
        </div>
      </div>
      <p className="mt-2 text-sm text-slate-700">
        <span className="font-medium">{TYPE_LABELS[criterion.criterion_type]}:</span>{" "}
        {describeParams(criterion)}
      </p>
      {criterion.accepted_evidence.length > 0 && (
        <p className="mt-1 text-xs text-slate-500">
          Evidence: {criterion.accepted_evidence.join(", ")}
        </p>
      )}
      {criterion.source_text && (
        <blockquote className="mt-2 border-l-2 border-slate-200 pl-3 text-xs italic text-slate-500">
          “{criterion.source_text}”
        </blockquote>
      )}
    </div>
  );
}
