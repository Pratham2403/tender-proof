"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { Tender } from "@/types";
import { StatusBadge } from "@/components/ui/badges";

const TABS = [
  { slug: "schema", label: "1 · Schema" },
  { slug: "bidders", label: "2 · Bidders" },
  { slug: "review", label: "3 · Review queue" },
  { slug: "report", label: "4 · Report" },
];

export function TenderNav({ tender }: { tender: Tender | null }) {
  const pathname = usePathname();

  return (
    <div className="mb-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <Link href="/" className="text-xs text-slate-400 hover:text-slate-600">
            ← All tenders
          </Link>
          <h1 className="text-xl font-bold tracking-tight">
            {tender?.title ?? "Loading…"}
          </h1>
        </div>
        {tender && <StatusBadge status={tender.status} />}
      </div>
      {tender && (
        <nav className="mt-4 flex gap-1 border-b border-slate-200">
          {TABS.map((tab) => {
            const href = `/tender/${tender.tender_id}/${tab.slug}`;
            const active = pathname === href;
            return (
              <Link
                key={tab.slug}
                href={href}
                className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium transition ${
                  active
                    ? "border-indigo-600 text-indigo-700"
                    : "border-transparent text-slate-500 hover:text-slate-800"
                }`}
              >
                {tab.label}
              </Link>
            );
          })}
        </nav>
      )}
    </div>
  );
}
