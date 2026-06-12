"use client";

import { useCallback, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import type { ReviewItem, Tender } from "@/types";
import { api } from "@/lib/api";
import { usePolling } from "@/lib/usePolling";
import { IconCheck, IconChevronRight } from "@/components/ui/icons";
import { Card, ListSkeleton, SectionLabel } from "@/components/ui/primitives";
import { TenderNav } from "@/components/TenderNav";
import { ReviewQueueItem } from "@/components/review/ReviewQueueItem";

export default function ReviewPage() {
  const { id } = useParams<{ id: string }>();
  const [tender, setTender] = useState<Tender | null>(null);
  const [items, setItems] = useState<ReviewItem[] | null>(null);

  const load = useCallback(async () => {
    const [t, q] = await Promise.all([
      api.getTender(id),
      api.getReviewQueue(id),
    ]);
    setTender(t);
    setItems(q);
  }, [id]);

  usePolling(load, 5000);

  return (
    <div className="animate-fade-up">
      <TenderNav tender={tender} />

      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-[15px] font-semibold text-slate-900">
            Human review queue
            {items && items.length > 0 && (
              <span className="ml-2 rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-semibold text-amber-700 ring-1 ring-inset ring-amber-600/25">
                {items.length} pending
              </span>
            )}
          </h2>
          <p className="mt-0.5 max-w-2xl text-sm text-slate-500">
            Uncertain verdicts ranked by impact × uncertainty — mandatory
            criteria surface first. Every decision here is written to the
            append-only audit log with your stated reason.
          </p>
        </div>
      </div>

      {!items && <ListSkeleton rows={2} />}

      {items && items.length === 0 && (
        <Card className="flex flex-col items-center justify-center px-8 py-14 text-center">
          <span className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600">
            <IconCheck className="h-5 w-5" />
          </span>
          <p className="text-sm font-semibold text-slate-700">
            Review queue is clear
          </p>
          <p className="mt-1 max-w-sm text-sm text-slate-500">
            Nothing is awaiting human judgment for this tender.
          </p>
          <Link
            href={`/tender/${id}/report`}
            className="mt-5 inline-flex items-center gap-1 text-sm font-medium text-indigo-600 transition-colors hover:text-indigo-700"
          >
            View final report
            <IconChevronRight className="h-4 w-4" />
          </Link>
        </Card>
      )}

      {items && items.length > 0 && (
        <div className="space-y-4">
          <SectionLabel>
            Highest impact first
          </SectionLabel>
          {items.map((item) => (
            <ReviewQueueItem
              key={item.item_id}
              tenderId={id}
              item={item}
              onResolved={load}
            />
          ))}
        </div>
      )}
    </div>
  );
}
