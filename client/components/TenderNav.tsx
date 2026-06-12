"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { Tender, TenderStatus } from "@/types";
import { StatusBadge } from "@/components/ui/badges";
import { IconArrowLeft, IconCheck } from "@/components/ui/icons";
import { Skeleton } from "@/components/ui/primitives";
import { formatDateTime } from "@/lib/format";

const STEPS = [
  { slug: "schema", label: "Schema review", description: "Verify extracted criteria" },
  { slug: "bidders", label: "Bidder submissions", description: "Upload & extract documents" },
  { slug: "review", label: "Human review", description: "Resolve uncertain verdicts" },
  { slug: "report", label: "Final report", description: "Consolidated verdicts" },
];

type StepState = "complete" | "active" | "upcoming";

function stepStates(status: TenderStatus): StepState[] {
  switch (status) {
    case "UPLOADING":
    case "COMPILING":
    case "PENDING_APPROVAL":
    case "FAILED":
      return ["active", "upcoming", "upcoming", "upcoming"];
    case "APPROVED":
      return ["complete", "active", "upcoming", "upcoming"];
    case "EVALUATING":
      return ["complete", "active", "upcoming", "upcoming"];
    case "COMPLETE":
      return ["complete", "complete", "active", "active"];
  }
}

export function TenderNav({ tender }: { tender: Tender | null }) {
  const pathname = usePathname();

  return (
    <div className="mb-8">
      <Link
        href="/"
        className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-400 transition-colors hover:text-slate-600"
      >
        <IconArrowLeft className="h-3.5 w-3.5" />
        All tenders
      </Link>

      <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
        {tender ? (
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-slate-900">
              {tender.title}
            </h1>
            <p className="mt-0.5 text-xs text-slate-400">
              Created {formatDateTime(tender.created_at)} ·{" "}
              {tender.bidder_count} bidder{tender.bidder_count === 1 ? "" : "s"}
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            <Skeleton className="h-6 w-80" />
            <Skeleton className="h-3 w-48" />
          </div>
        )}
        {tender && <StatusBadge status={tender.status} />}
      </div>

      {tender && (
        <nav
          aria-label="Evaluation workflow"
          className="mt-6 grid grid-cols-2 gap-2 lg:grid-cols-4"
        >
          {STEPS.map((step, i) => {
            const state = stepStates(tender.status)[i];
            const href = `/tender/${tender.tender_id}/${step.slug}`;
            const current = pathname === href;
            return (
              <Link
                key={step.slug}
                href={href}
                aria-current={current ? "step" : undefined}
                className={`group relative flex items-start gap-3 rounded-xl border p-3.5 transition-all duration-150 ${
                  current
                    ? "border-indigo-300 bg-indigo-50/70 shadow-[0_1px_2px_rgba(79,70,229,0.08)]"
                    : "border-slate-200/80 bg-white hover:border-slate-300 hover:bg-slate-50/80"
                }`}
              >
                <span
                  className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold transition-colors ${
                    state === "complete"
                      ? "bg-emerald-100 text-emerald-700"
                      : state === "active"
                        ? "bg-indigo-600 text-white"
                        : "bg-slate-100 text-slate-400"
                  }`}
                >
                  {state === "complete" ? (
                    <IconCheck className="h-3.5 w-3.5" />
                  ) : (
                    i + 1
                  )}
                </span>
                <span className="min-w-0">
                  <span
                    className={`block truncate text-[13px] font-semibold ${
                      current ? "text-indigo-900" : "text-slate-700"
                    }`}
                  >
                    {step.label}
                  </span>
                  <span className="mt-0.5 hidden text-xs text-slate-400 xl:block">
                    {step.description}
                  </span>
                </span>
              </Link>
            );
          })}
        </nav>
      )}
    </div>
  );
}
