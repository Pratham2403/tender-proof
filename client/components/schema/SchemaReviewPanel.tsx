"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { Criterion, EvaluationSchema } from "@/types";
import { api } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { Button } from "@/components/ui/primitives";
import { IconCheck } from "@/components/ui/icons";
import { useToast } from "@/components/ui/toast";
import { CriterionCard } from "./CriterionCard";

export function SchemaReviewPanel({
  tenderId,
  schema,
}: {
  tenderId: string;
  schema: EvaluationSchema;
}) {
  const router = useRouter();
  const toast = useToast();
  const [criteria, setCriteria] = useState<Criterion[]>(schema.criteria);
  const [edited, setEdited] = useState(false);
  const [approving, setApproving] = useState(false);
  const approved = schema.status === "APPROVED";
  const mandatoryCount = criteria.filter((c) => c.mandatory).length;

  const approve = async () => {
    setApproving(true);
    try {
      await api.approveSchema(tenderId, edited ? criteria : undefined);
      toast("success", "Schema approved — bidder uploads are now open.");
      router.push(`/tender/${tenderId}/bidders`);
    } catch (err) {
      toast("error", err instanceof Error ? err.message : "Approval failed");
      setApproving(false);
    }
  };

  return (
    <div className="pb-24">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-[15px] font-semibold text-slate-900">
            Extracted eligibility criteria
          </h2>
          <p className="mt-0.5 text-sm text-slate-500">
            {criteria.length} criteria · {mandatoryCount} mandatory. Verify
            each against the tender text — evaluation cannot begin until the
            schema is approved.
          </p>
        </div>
        {approved && (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1.5 text-sm font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-600/20">
            <IconCheck className="h-4 w-4" />
            Approved
            {schema.approved_at && (
              <span className="font-normal text-emerald-600/80">
                · {formatDateTime(schema.approved_at)}
              </span>
            )}
          </span>
        )}
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {criteria.map((c, i) => (
          <CriterionCard
            key={c.criterion_id}
            criterion={c}
            editable={!approved}
            onToggleMandatory={() => {
              setCriteria((prev) =>
                prev.map((x, j) =>
                  j === i ? { ...x, mandatory: !x.mandatory } : x,
                ),
              );
              setEdited(true);
            }}
            onRemove={() => {
              setCriteria((prev) => prev.filter((_, j) => j !== i));
              setEdited(true);
              toast("info", `${c.label} removed from schema.`);
            }}
          />
        ))}
      </div>

      {!approved && (
        <div className="fixed inset-x-0 bottom-0 z-30 border-t border-slate-200/80 bg-white/90 backdrop-blur-md">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-3.5">
            <p className="text-sm text-slate-500">
              <span className="font-semibold text-slate-700">
                {criteria.length}
              </span>{" "}
              criteria ready
              {edited && (
                <span className="ml-2 rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700 ring-1 ring-inset ring-amber-600/20">
                  edited
                </span>
              )}
            </p>
            <Button
              variant="success"
              onClick={approve}
              loading={approving}
              disabled={criteria.length === 0}
            >
              <IconCheck className="h-4 w-4" />
              {edited ? "Approve edited schema" : "Approve schema"}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
