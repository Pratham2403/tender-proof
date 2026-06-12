"use client";

import { useCallback, useState } from "react";
import Link from "next/link";
import type { Tender, TenderStatus } from "@/types";
import { api } from "@/lib/api";
import { timeAgo } from "@/lib/format";
import { usePolling } from "@/lib/usePolling";
import { StatusBadge } from "@/components/ui/badges";
import {
  IconChevronRight,
  IconDocument,
  IconShield,
} from "@/components/ui/icons";
import {
  Alert,
  Card,
  EmptyState,
  ListSkeleton,
  SectionLabel,
} from "@/components/ui/primitives";
import { TenderUpload } from "@/components/upload/TenderUpload";

const NEXT_STEP: Partial<Record<TenderStatus, { href: string; label: string }>> = {
  COMPILING: { href: "schema", label: "View progress" },
  PENDING_APPROVAL: { href: "schema", label: "Review schema" },
  APPROVED: { href: "bidders", label: "Upload bidders" },
  EVALUATING: { href: "bidders", label: "View progress" },
  COMPLETE: { href: "report", label: "View report" },
  FAILED: { href: "schema", label: "View details" },
};

function Kpi({ label, value, tone = "text-slate-900" }: {
  label: string;
  value: number;
  tone?: string;
}) {
  return (
    <Card className="px-5 py-4">
      <p className="text-xs font-medium text-slate-400">{label}</p>
      <p className={`mt-1 text-2xl font-semibold tabular-nums tracking-tight ${tone}`}>
        {value}
      </p>
    </Card>
  );
}

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

  usePolling(load, 5000);

  const counts = {
    total: tenders?.length ?? 0,
    awaiting: tenders?.filter((t) => t.status === "PENDING_APPROVAL").length ?? 0,
    evaluating:
      tenders?.filter((t) => ["COMPILING", "APPROVED", "EVALUATING"].includes(t.status))
        .length ?? 0,
    complete: tenders?.filter((t) => t.status === "COMPLETE").length ?? 0,
  };

  return (
    <div className="animate-fade-up space-y-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
            Procurement dashboard
          </h1>
          <p className="mt-1 max-w-xl text-sm leading-relaxed text-slate-500">
            Upload a tender, approve its compiled eligibility schema, then
            evaluate every bidder with a fully cited, auditable verdict trail.
          </p>
        </div>
        <div className="hidden items-center gap-2 text-xs text-slate-400 lg:flex">
          <IconShield className="h-4 w-4" />
          Deterministic verdicts · append-only audit log
        </div>
      </div>

      {tenders && tenders.length > 0 && (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Kpi label="Total tenders" value={counts.total} />
          <Kpi label="Awaiting approval" value={counts.awaiting} tone="text-amber-600" />
          <Kpi label="In progress" value={counts.evaluating} tone="text-sky-600" />
          <Kpi label="Complete" value={counts.complete} tone="text-emerald-600" />
        </div>
      )}

      <TenderUpload onCreated={load} />

      <section>
        <div className="mb-3">
          <SectionLabel>Tenders</SectionLabel>
        </div>

        {error && (
          <Alert tone="error">
            {error} — is the backend running on port 8000?
          </Alert>
        )}

        {!tenders && !error && <ListSkeleton rows={3} />}

        {tenders && tenders.length === 0 && (
          <EmptyState
            icon={<IconDocument className="h-5 w-5" />}
            title="No tenders yet"
            description="Upload a tender document above — its eligibility criteria will be compiled into a reviewable schema within seconds."
          />
        )}

        <ul className="space-y-3">
          {tenders?.map((t) => {
            const next = NEXT_STEP[t.status];
            const href = `/tender/${t.tender_id}/${next?.href ?? "schema"}`;
            return (
              <li key={t.tender_id}>
                <Link
                  href={href}
                  className="group flex items-center justify-between gap-4 rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04)] transition-all duration-150 hover:border-slate-300 hover:shadow-[0_4px_12px_rgba(15,23,42,0.06)]"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-slate-900">
                      {t.title}
                    </p>
                    <p className="mt-1 text-xs text-slate-400">
                      Created {timeAgo(t.created_at)} · {t.bidder_count} bidder
                      {t.bidder_count === 1 ? "" : "s"}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-3">
                    <StatusBadge status={t.status} />
                    {next && (
                      <span className="hidden items-center gap-1 text-sm font-medium text-indigo-600 transition-colors group-hover:text-indigo-700 sm:flex">
                        {next.label}
                        <IconChevronRight className="h-4 w-4 transition-transform duration-150 group-hover:translate-x-0.5" />
                      </span>
                    )}
                  </div>
                </Link>
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );
}
