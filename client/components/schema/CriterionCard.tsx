"use client";

import type { Criterion, CriterionType } from "@/types";
import {
  IconBuilding,
  IconClock,
  IconEye,
  IconHash,
  IconScale,
  IconX,
} from "@/components/ui/icons";

const TYPE_META: Record<
  CriterionType,
  { label: string; icon: React.ReactNode; tint: string }
> = {
  CurrencyThreshold: {
    label: "Currency threshold",
    icon: <IconBuilding className="h-4 w-4" />,
    tint: "bg-sky-50 text-sky-600",
  },
  CountMinimum: {
    label: "Count minimum",
    icon: <IconHash className="h-4 w-4" />,
    tint: "bg-violet-50 text-violet-600",
  },
  BooleanPresence: {
    label: "Presence check",
    icon: <IconEye className="h-4 w-4" />,
    tint: "bg-teal-50 text-teal-600",
  },
  DateRange: {
    label: "Date validity",
    icon: <IconClock className="h-4 w-4" />,
    tint: "bg-amber-50 text-amber-600",
  },
  SimilarityScore: {
    label: "Similarity judgment",
    icon: <IconScale className="h-4 w-4" />,
    tint: "bg-rose-50 text-rose-600",
  },
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
      return vals.length
        ? `must contain: ${vals.join(" / ")}`
        : "must be present";
    }
    case "DateRange":
      return (
        [
          p.not_expired_as_of
            ? `not expired as of ${String(p.not_expired_as_of).slice(0, 10)}`
            : null,
          p.issued_after
            ? `issued after ${String(p.issued_after).slice(0, 10)}`
            : null,
        ]
          .filter(Boolean)
          .join(", ") || "any valid date"
      );
    case "SimilarityScore":
      return `pass ≥ ${p.pass_threshold ?? 0.7} · fail ≤ ${p.fail_threshold ?? 0.4}`;
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
  const meta = TYPE_META[criterion.criterion_type];

  return (
    <div className="group flex flex-col rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04)] transition-shadow duration-150 hover:shadow-[0_4px_12px_rgba(15,23,42,0.06)]">
      <div className="flex items-start gap-3">
        <span
          className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${meta.tint}`}
        >
          {meta.icon}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[11px] font-medium text-slate-400">
              {criterion.criterion_id}
            </span>
            <span className="text-[11px] text-slate-300">·</span>
            <span className="text-[11px] font-medium text-slate-400">
              {meta.label}
            </span>
          </div>
          <h3 className="mt-0.5 truncate text-sm font-semibold text-slate-900">
            {criterion.label}
          </h3>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          {editable ? (
            <button
              type="button"
              onClick={onToggleMandatory}
              title="Toggle mandatory"
              className={`rounded-full px-2.5 py-1 text-[11px] font-semibold transition-colors ${
                criterion.mandatory
                  ? "bg-indigo-50 text-indigo-700 ring-1 ring-inset ring-indigo-600/20 hover:bg-indigo-100"
                  : "bg-slate-100 text-slate-500 hover:bg-slate-200"
              }`}
            >
              {criterion.mandatory ? "Mandatory" : "Optional"}
            </button>
          ) : (
            <span
              className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${
                criterion.mandatory
                  ? "bg-indigo-50 text-indigo-700 ring-1 ring-inset ring-indigo-600/20"
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
              className="rounded-lg p-1.5 text-slate-300 opacity-0 transition-all hover:bg-rose-50 hover:text-rose-600 group-hover:opacity-100"
              title="Remove criterion"
              aria-label={`Remove ${criterion.label}`}
            >
              <IconX className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>

      <p className="mt-3 rounded-lg bg-slate-50 px-3 py-2 font-mono text-xs text-slate-700">
        {describeParams(criterion)}
      </p>

      {criterion.accepted_evidence.length > 0 && (
        <p className="mt-2.5 text-xs text-slate-500">
          <span className="font-medium text-slate-600">Evidence:</span>{" "}
          {criterion.accepted_evidence.join(", ")}
        </p>
      )}
      {criterion.source_text && (
        <blockquote className="mt-2.5 border-l-2 border-indigo-200 pl-3 text-xs italic leading-relaxed text-slate-400">
          “{criterion.source_text}”
        </blockquote>
      )}
    </div>
  );
}
