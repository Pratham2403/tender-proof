import type { BidderStatus, TenderStatus, Verdict } from "@/types";

const VERDICT_STYLES: Record<Verdict, { wrap: string; dot: string }> = {
  PASS: {
    wrap: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
    dot: "bg-emerald-500",
  },
  FAIL: {
    wrap: "bg-rose-50 text-rose-700 ring-rose-600/20",
    dot: "bg-rose-500",
  },
  REVIEW: {
    wrap: "bg-amber-50 text-amber-700 ring-amber-600/25",
    dot: "bg-amber-500",
  },
};

export function VerdictBadge({
  verdict,
  size = "md",
}: {
  verdict: Verdict;
  size?: "sm" | "md";
}) {
  const s = VERDICT_STYLES[verdict];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-semibold ring-1 ring-inset ${s.wrap} ${
        size === "sm" ? "px-2 py-px text-[10px]" : "px-2.5 py-0.5 text-xs"
      }`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
      {verdict}
    </span>
  );
}

const STATUS_META: Record<
  string,
  { label: string; wrap: string; active?: boolean }
> = {
  UPLOADING: { label: "Uploading", wrap: "bg-slate-100 text-slate-600", active: true },
  COMPILING: { label: "Compiling schema", wrap: "bg-sky-50 text-sky-700 ring-1 ring-inset ring-sky-600/20", active: true },
  PENDING_APPROVAL: { label: "Awaiting approval", wrap: "bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-600/25" },
  APPROVED: { label: "Schema approved", wrap: "bg-indigo-50 text-indigo-700 ring-1 ring-inset ring-indigo-600/20" },
  EVALUATING: { label: "Evaluating", wrap: "bg-sky-50 text-sky-700 ring-1 ring-inset ring-sky-600/20", active: true },
  COMPLETE: { label: "Complete", wrap: "bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-600/20" },
  FAILED: { label: "Failed", wrap: "bg-rose-50 text-rose-700 ring-1 ring-inset ring-rose-600/20" },
  QUEUED: { label: "Queued", wrap: "bg-slate-100 text-slate-600" },
  EXTRACTING: { label: "Extracting", wrap: "bg-sky-50 text-sky-700 ring-1 ring-inset ring-sky-600/20", active: true },
  EVALUATED: { label: "Evaluated", wrap: "bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-600/20" },
};

export function StatusBadge({
  status,
}: {
  status: TenderStatus | BidderStatus;
}) {
  const meta = STATUS_META[status] ?? {
    label: status,
    wrap: "bg-slate-100 text-slate-600",
  };
  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium ${meta.wrap}`}
    >
      {meta.active && (
        <span className="animate-soft-pulse h-1.5 w-1.5 rounded-full bg-current" />
      )}
      {meta.label}
    </span>
  );
}

export function ConfidenceBar({ confidence }: { confidence: number }) {
  const value = Math.round(confidence * 100);
  const color =
    confidence >= 0.7
      ? "bg-emerald-500"
      : confidence >= 0.4
        ? "bg-amber-500"
        : "bg-rose-400";
  return (
    <span className="inline-flex items-center gap-2" title={`Extraction confidence ${value}%`}>
      <span className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-200/80">
        <span
          className={`block h-full rounded-full ${color}`}
          style={{ width: `${value}%` }}
        />
      </span>
      <span className="text-xs tabular-nums text-slate-500">{value}%</span>
    </span>
  );
}
