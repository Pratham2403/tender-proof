"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import type { Bidder, Tender } from "@/types";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/ui/badges";
import { TenderNav } from "@/components/TenderNav";
import { BidderUpload } from "@/components/upload/BidderUpload";

export default function BiddersPage() {
  const { id } = useParams<{ id: string }>();
  const [tender, setTender] = useState<Tender | null>(null);
  const [bidders, setBidders] = useState<Bidder[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [t, b] = await Promise.all([
        api.getTender(id),
        api.listBidders(id),
      ]);
      setTender(t);
      setBidders(b);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    }
  }, [id]);

  useEffect(() => {
    load();
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, [load]);

  const schemaApproved =
    tender &&
    ["APPROVED", "EVALUATING", "COMPLETE"].includes(tender.status);

  return (
    <div>
      <TenderNav tender={tender} />
      {error && (
        <p className="mb-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-600">
          {error}
        </p>
      )}

      {schemaApproved ? (
        <BidderUpload tenderId={id} onUploaded={load} />
      ) : (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          The evaluation schema must be approved before bidder submissions can
          be uploaded.{" "}
          <Link href={`/tender/${id}/schema`} className="font-semibold underline">
            Review schema
          </Link>
        </div>
      )}

      <section className="mt-6">
        <h2 className="mb-3 text-base font-semibold">
          Bidder submissions ({bidders.length})
        </h2>
        {bidders.length === 0 && (
          <p className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-400">
            No bidder submissions yet.
          </p>
        )}
        <ul className="space-y-3">
          {bidders.map((b) => (
            <li
              key={b.bidder_id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-4"
            >
              <div>
                <p className="text-sm font-semibold">{b.company_name}</p>
                <p className="mt-0.5 text-xs text-slate-500">
                  {b.file_names.join(", ")}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <StatusBadge status={b.status} />
                {(b.status === "EXTRACTING" || b.status === "EVALUATING") && (
                  <span className="h-3 w-3 animate-spin rounded-full border-2 border-sky-500 border-t-transparent" />
                )}
              </div>
            </li>
          ))}
        </ul>
        {bidders.some((b) => b.status === "EVALUATED") && (
          <div className="mt-4 flex gap-4">
            <Link
              href={`/tender/${id}/report`}
              className="text-sm font-medium text-indigo-600 hover:text-indigo-800"
            >
              View consolidated report →
            </Link>
            <Link
              href={`/tender/${id}/review`}
              className="text-sm font-medium text-amber-600 hover:text-amber-800"
            >
              Open review queue →
            </Link>
          </div>
        )}
      </section>
    </div>
  );
}
