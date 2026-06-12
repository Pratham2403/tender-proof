import type { BidderStatus, TenderStatus, Verdict } from "@/types";

const VERDICT_STYLES: Record<Verdict, string> = {
  PASS: "bg-emerald-100 text-emerald-700 ring-emerald-200",
  FAIL: "bg-rose-100 text-rose-700 ring-rose-200",
  REVIEW: "bg-amber-100 text-amber-700 ring-amber-200",
};

export function VerdictBadge({ verdict }: { verdict: Verdict }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ${VERDICT_STYLES[verdict]}`}
    >
      {verdict}
    </span>
  );
}

const STATUS_STYLES: Record<string, string> = {
  UPLOADING: "bg-slate-100 text-slate-600",
  COMPILING: "bg-sky-100 text-sky-700",
  PENDING_APPROVAL: "bg-amber-100 text-amber-700",
  APPROVED: "bg-indigo-100 text-indigo-700",
  EVALUATING: "bg-sky-100 text-sky-700",
  COMPLETE: "bg-emerald-100 text-emerald-700",
  EVALUATED: "bg-emerald-100 text-emerald-700",
  FAILED: "bg-rose-100 text-rose-700",
  QUEUED: "bg-slate-100 text-slate-600",
  EXTRACTING: "bg-sky-100 text-sky-700",
};

export function StatusBadge({
  status,
}: {
  status: TenderStatus | BidderStatus;
}) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_STYLES[status] ?? "bg-slate-100 text-slate-600"}`}
    >
      {status.replace(/_/g, " ")}
    </span>
  );
}

export function ConfidenceBar({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  const color =
    confidence >= 0.7
      ? "bg-emerald-500"
      : confidence >= 0.4
        ? "bg-amber-500"
        : "bg-rose-500";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-200">
        <div className={`h-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs tabular-nums text-slate-500">{pct}%</span>
    </div>
  );
}
