"use client";

import { useCallback, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import type { ReviewItem, Tender } from "@/types";
import { api } from "@/lib/api";
import { usePolling } from "@/lib/usePolling";
import { TenderNav } from "@/components/TenderNav";
import { ReviewQueueItem } from "@/components/review/ReviewQueueItem";

export default function ReviewPage() {
  const { id } = useParams<{ id: string }>();
  const [tender, setTender] = useState<Tender | null>(null);
  const [items, setItems] = useState<ReviewItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [t, q] = await Promise.all([
        api.getTender(id),
        api.getReviewQueue(id),
      ]);
      setTender(t);
      setItems(q);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load queue");
    }
  }, [id]);

  usePolling(load, 5000);

  return (
    <div>
      <TenderNav tender={tender} />
      <div className="mb-4">
        <h2 className="text-base font-semibold">Human review queue</h2>
        <p className="text-sm text-slate-500">
          Ambiguous or low-confidence verdicts, ranked by impact ×
          uncertainty. Every decision you make here is written to the
          append-only audit log.
        </p>
      </div>
      {error && (
        <p className="mb-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-600">
          {error}
        </p>
      )}
      {items && items.length === 0 && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-8 text-center text-sm text-emerald-700">
          Review queue is clear — nothing awaiting human judgment.{" "}
          <Link href={`/tender/${id}/report`} className="font-semibold underline">
            View report
          </Link>
        </div>
      )}
      <div className="space-y-4">
        {items?.map((item) => (
          <ReviewQueueItem
            key={item.item_id}
            tenderId={id}
            item={item}
            onResolved={load}
          />
        ))}
      </div>
    </div>
  );
}
