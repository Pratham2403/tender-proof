"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import type { Tender, TenderStatus } from "@/types";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/ui/badges";
import { TenderUpload } from "@/components/upload/TenderUpload";

const NEXT_STEP: Partial<Record<TenderStatus, { href: string; label: string }>> = {
  PENDING_APPROVAL: { href: "schema", label: "Review schema →" },
  APPROVED: { href: "bidders", label: "Upload bidders →" },
  EVALUATING: { href: "bidders", label: "View progress →" },
  COMPLETE: { href: "report", label: "View report →" },
};

export default function Dashboard() {
  const [tenders, setTenders] = useState<Tender[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setTenders(await api.listTenders());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load tenders");
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [load]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          Procurement dashboard
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Upload a tender, approve its compiled eligibility schema, then
          evaluate bidder submissions with a fully auditable verdict trail.
        </p>
      </div>

      <TenderUpload onCreated={load} />

      <section>
        <h2 className="mb-3 text-base font-semibold">Tenders</h2>
        {error && (
          <p className="rounded-lg bg-rose-50 p-3 text-sm text-rose-600">
            {error} — is the backend running on port 8000?
          </p>
        )}
        {tenders && tenders.length === 0 && (
          <p className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-400">
            No tenders yet. Upload one above to get started.
          </p>
        )}
        <ul className="space-y-3">
          {tenders?.map((t) => {
            const next = NEXT_STEP[t.status];
            return (
              <li
                key={t.tender_id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-4"
              >
                <div>
                  <p className="text-sm font-semibold">{t.title}</p>
                  <p className="mt-0.5 text-xs text-slate-500">
                    {new Date(t.created_at).toLocaleString()} ·{" "}
                    {t.bidder_count} bidder(s)
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <StatusBadge status={t.status} />
                  {next && (
                    <Link
                      href={`/tender/${t.tender_id}/${next.href}`}
                      className="text-sm font-medium text-indigo-600 hover:text-indigo-800"
                    >
                      {next.label}
                    </Link>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );
}
