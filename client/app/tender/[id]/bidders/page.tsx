"use client";

import { useCallback, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import type { Bidder, BidderStatus, Tender } from "@/types";
import { api } from "@/lib/api";
import { timeAgo } from "@/lib/format";
import { usePolling } from "@/lib/usePolling";
import { StatusBadge } from "@/components/ui/badges";
import {
  IconBuilding,
  IconChevronRight,
  IconDocument,
  Spinner,
} from "@/components/ui/icons";
import {
  Alert,
  Card,
  EmptyState,
  ListSkeleton,
  SectionLabel,
} from "@/components/ui/primitives";
import { TenderNav } from "@/components/TenderNav";
import { BidderUpload } from "@/components/upload/BidderUpload";

const PIPELINE: BidderStatus[] = ["QUEUED", "EXTRACTING", "EVALUATING", "EVALUATED"];

function PipelineDots({ status }: { status: BidderStatus }) {
  if (status === "FAILED") return null;
  const reached = PIPELINE.indexOf(status);
  return (
    <span className="hidden items-center gap-1 md:flex" title={`Stage: ${status}`}>
      {PIPELINE.map((stage, i) => (
        <span
          key={stage}
          className={`h-1.5 w-5 rounded-full transition-colors duration-300 ${
            i < reached
              ? "bg-emerald-400"
              : i === reached
                ? status === "EVALUATED"
                  ? "bg-emerald-400"
                  : "animate-soft-pulse bg-sky-400"
                : "bg-slate-200"
          }`}
        />
      ))}
    </span>
  );
}

export default function BiddersPage() {
  const { id } = useParams<{ id: string }>();
  const [tender, setTender] = useState<Tender | null>(null);
  const [bidders, setBidders] = useState<Bidder[] | null>(null);

  const load = useCallback(async () => {
    const [t, b] = await Promise.all([api.getTender(id), api.listBidders(id)]);
    setTender(t);
    setBidders(b);
  }, [id]);

  usePolling(load, 4000);

  const schemaApproved =
    tender && ["APPROVED", "EVALUATING", "COMPLETE"].includes(tender.status);
  const anyEvaluated = bidders?.some((b) => b.status === "EVALUATED") ?? false;

  return (
    <div className="animate-fade-up">
      <TenderNav tender={tender} />

      {schemaApproved ? (
        <BidderUpload tenderId={id} onUploaded={load} />
      ) : (
        tender && (
          <Alert tone="warning">
            The evaluation schema must be approved before bidder submissions
            can be uploaded.{" "}
            <Link
              href={`/tender/${id}/schema`}
              className="font-semibold underline underline-offset-2 hover:text-amber-900"
            >
              Review schema →
            </Link>
          </Alert>
        )
      )}

      <section className="mt-8">
        <div className="mb-3 flex items-center justify-between">
          <SectionLabel>
            Bidder submissions{bidders ? ` · ${bidders.length}` : ""}
          </SectionLabel>
          {anyEvaluated && (
            <Link
              href={`/tender/${id}/report`}
              className="flex items-center gap-1 text-sm font-medium text-indigo-600 transition-colors hover:text-indigo-700"
            >
              View consolidated report
              <IconChevronRight className="h-4 w-4" />
            </Link>
          )}
        </div>

        {!bidders && <ListSkeleton rows={2} />}

        {bidders && bidders.length === 0 && (
          <EmptyState
            icon={<IconBuilding className="h-5 w-5" />}
            title="No bidder submissions yet"
            description={
              schemaApproved
                ? "Add the first bidder package above — extraction and evaluation start automatically."
                : "Approve the schema first, then upload bidder document packages here."
            }
          />
        )}

        <ul className="space-y-3">
          {bidders?.map((b) => (
            <li key={b.bidder_id}>
              <Card className="flex flex-wrap items-center justify-between gap-3 p-5">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-slate-900">
                    {b.company_name}
                  </p>
                  <p className="mt-1 flex items-center gap-1.5 text-xs text-slate-400">
                    <IconDocument className="h-3.5 w-3.5" />
                    <span className="truncate">{b.file_names.join(", ")}</span>
                    <span>· {timeAgo(b.submitted_at)}</span>
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-4">
                  <PipelineDots status={b.status} />
                  <StatusBadge status={b.status} />
                  {(b.status === "EXTRACTING" || b.status === "EVALUATING") && (
                    <Spinner className="h-4 w-4 text-sky-500" />
                  )}
                </div>
              </Card>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
