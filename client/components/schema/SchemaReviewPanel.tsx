"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { Criterion, EvaluationSchema } from "@/types";
import { api } from "@/lib/api";
import { CriterionCard } from "./CriterionCard";

export function SchemaReviewPanel({
  tenderId,
  schema,
}: {
  tenderId: string;
  schema: EvaluationSchema;
}) {
  const router = useRouter();
  const [criteria, setCriteria] = useState<Criterion[]>(schema.criteria);
  const [edited, setEdited] = useState(false);
  const [approving, setApproving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const approved = schema.status === "APPROVED";

  const approve = async () => {
    setApproving(true);
    setError(null);
    try {
      await api.approveSchema(tenderId, edited ? criteria : undefined);
      router.push(`/tender/${tenderId}/bidders`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approval failed");
      setApproving(false);
    }
  };

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold">
            Extracted eligibility criteria ({criteria.length})
          </h2>
          <p className="text-sm text-slate-500">
            Review each criterion against the tender text. Evaluation cannot
            begin until the schema is approved.
          </p>
        </div>
        {!approved && (
          <button
            onClick={approve}
            disabled={approving || criteria.length === 0}
            className="rounded-lg bg-emerald-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:opacity-40"
          >
            {approving
              ? "Approving…"
              : edited
                ? "Approve edited schema"
                : "Approve schema"}
          </button>
        )}
        {approved && (
          <span className="rounded-full bg-emerald-100 px-3 py-1 text-sm font-medium text-emerald-700">
            Approved
          </span>
        )}
      </div>
      {error && <p className="mb-3 text-sm text-rose-600">{error}</p>}
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
            }}
          />
        ))}
      </div>
    </div>
  );
}
