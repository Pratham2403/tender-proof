"use client";

import { useState } from "react";
import type { ReviewItem } from "@/types";
import { api } from "@/lib/api";
import { ConfidenceBar } from "@/components/ui/badges";
import { IconCheck, IconDocument, IconX } from "@/components/ui/icons";
import { Button, Card } from "@/components/ui/primitives";
import { useToast } from "@/components/ui/toast";

export function ReviewQueueItem({
  tenderId,
  item,
  onResolved,
}: {
  tenderId: string;
  item: ReviewItem;
  onResolved: () => void;
}) {
  const toast = useToast();
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState<"PASS" | "FAIL" | null>(null);

  const resolve = async (verdict: "PASS" | "FAIL") => {
    setBusy(verdict);
    try {
      await api.resolveReviewItem(tenderId, item.item_id, verdict, reason, "override");
      toast(
        "success",
        `${item.criterion_id} for ${item.company_name} resolved as ${verdict}.`,
      );
      onResolved();
    } catch (err) {
      toast("error", err instanceof Error ? err.message : "Failed to resolve");
      setBusy(null);
    }
  };

  return (
    <Card
      className={`overflow-hidden border-l-4 ${item.mandatory ? "border-l-amber-400" : "border-l-slate-200"}`}
    >
      <div className="p-5">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-[11px] font-medium text-slate-400">
                {item.criterion_id}
              </span>
              <h3 className="text-sm font-semibold text-slate-900">
                {item.label}
              </h3>
              {item.mandatory && (
                <span className="rounded-full bg-indigo-50 px-2 py-px text-[10px] font-semibold text-indigo-600 ring-1 ring-inset ring-indigo-600/20">
                  MANDATORY
                </span>
              )}
            </div>
            <p className="mt-0.5 text-xs text-slate-400">
              {item.company_name}
            </p>
          </div>
          <ConfidenceBar confidence={item.confidence} />
        </div>

        <p className="mt-3 text-sm leading-relaxed text-slate-600">
          {item.reason}
        </p>

        <dl className="mt-4 grid gap-x-6 gap-y-2.5 rounded-xl bg-slate-50 p-4 text-xs sm:grid-cols-2">
          <div>
            <dt className="font-semibold uppercase tracking-wide text-slate-400">
              Extracted value
            </dt>
            <dd className="mt-1 font-mono text-[13px] text-slate-800">
              {item.extracted_value ?? "— not found —"}
            </dd>
          </div>
          <div>
            <dt className="font-semibold uppercase tracking-wide text-slate-400">
              Source
            </dt>
            <dd className="mt-1 flex items-center gap-1.5 text-[13px] text-slate-800">
              {item.document_name ? (
                <>
                  <IconDocument className="h-3.5 w-3.5 text-slate-400" />
                  {item.document_name}
                  {item.page_number ? `, p.${item.page_number}` : ""}
                </>
              ) : (
                "—"
              )}
            </dd>
          </div>
          {item.raw_text && (
            <div className="sm:col-span-2">
              <dt className="font-semibold uppercase tracking-wide text-slate-400">
                Supporting passage
              </dt>
              <dd className="mt-1 border-l-2 border-slate-200 pl-3 text-[13px] italic leading-relaxed text-slate-600">
                “{item.raw_text}”
              </dd>
            </div>
          )}
        </dl>

        <div className="mt-4 flex flex-col gap-2.5 sm:flex-row sm:items-center">
          <input
            type="text"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Officer reason — recorded in the audit trail"
            className="flex-1 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-sm shadow-sm outline-none transition-shadow placeholder:text-slate-400 focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100"
          />
          <div className="flex shrink-0 gap-2">
            <Button
              variant="success"
              loading={busy === "PASS"}
              disabled={busy !== null}
              onClick={() => resolve("PASS")}
            >
              <IconCheck className="h-4 w-4" />
              Confirm PASS
            </Button>
            <Button
              variant="danger"
              loading={busy === "FAIL"}
              disabled={busy !== null}
              onClick={() => resolve("FAIL")}
            >
              <IconX className="h-4 w-4" />
              Override FAIL
            </Button>
          </div>
        </div>
      </div>
    </Card>
  );
}
