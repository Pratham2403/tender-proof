"use client";

import { useState } from "react";
import type { ReviewItem } from "@/types";
import { api } from "@/lib/api";
import { ConfidenceBar } from "@/components/ui/badges";

export function ReviewQueueItem({
  tenderId,
  item,
  onResolved,
}: {
  tenderId: string;
  item: ReviewItem;
  onResolved: () => void;
}) {
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const resolve = async (verdict: "PASS" | "FAIL") => {
    setBusy(true);
    setError(null);
    try {
      await api.resolveReviewItem(tenderId, item.item_id, verdict, reason, "override");
      onResolved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to resolve");
      setBusy(false);
    }
  };

  return (
    <div className="rounded-xl border border-amber-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs text-slate-500">
            {item.criterion_id}
          </span>
          <span className="text-sm font-semibold">{item.label}</span>
          {item.mandatory && (
            <span className="rounded bg-indigo-50 px-1.5 text-[10px] font-medium text-indigo-600">
              MANDATORY
            </span>
          )}
        </div>
        <span className="text-sm text-slate-600">{item.company_name}</span>
      </div>

      <p className="mt-2 text-sm text-slate-700">{item.reason}</p>

      <div className="mt-3 grid gap-2 rounded-lg bg-slate-50 p-3 text-xs text-slate-600 sm:grid-cols-2">
        <div>
          <span className="font-medium">Extracted value:</span>{" "}
          {item.extracted_value ?? "— not found —"}
        </div>
        <div>
          <span className="font-medium">Source:</span>{" "}
          {item.document_name
            ? `${item.document_name}${item.page_number ? `, p.${item.page_number}` : ""}`
            : "—"}
        </div>
        {item.raw_text && (
          <div className="sm:col-span-2">
            <span className="font-medium">Supporting passage:</span>{" "}
            <em>“{item.raw_text}”</em>
          </div>
        )}
        <div className="flex items-center gap-2 sm:col-span-2">
          <span className="font-medium">Extraction confidence:</span>
          <ConfidenceBar confidence={item.confidence} />
        </div>
      </div>

      <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center">
        <input
          type="text"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Officer reason (logged to audit trail)"
          className="flex-1 rounded-lg border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-indigo-500"
        />
        <div className="flex gap-2">
          <button
            onClick={() => resolve("PASS")}
            disabled={busy}
            className="rounded-lg bg-emerald-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-40"
          >
            Confirm PASS
          </button>
          <button
            onClick={() => resolve("FAIL")}
            disabled={busy}
            className="rounded-lg bg-rose-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-rose-700 disabled:opacity-40"
          >
            Override FAIL
          </button>
        </div>
      </div>
      {error && <p className="mt-2 text-sm text-rose-600">{error}</p>}
    </div>
  );
}
