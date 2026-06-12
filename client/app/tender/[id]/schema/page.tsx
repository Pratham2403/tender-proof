"use client";

import { useCallback, useState } from "react";
import { useParams } from "next/navigation";
import type { EvaluationSchema, Tender } from "@/types";
import { api } from "@/lib/api";
import { usePolling } from "@/lib/usePolling";
import { TenderNav } from "@/components/TenderNav";
import { SchemaReviewPanel } from "@/components/schema/SchemaReviewPanel";

export default function SchemaPage() {
  const { id } = useParams<{ id: string }>();
  const [tender, setTender] = useState<Tender | null>(null);
  const [schema, setSchema] = useState<EvaluationSchema | null>(null);

  const load = useCallback(async () => {
    const t = await api.getTender(id);
    setTender(t);
    try {
      setSchema(await api.getSchema(id));
    } catch {
      // Schema not compiled yet — polling continues while the worker runs
    }
  }, [id]);

  usePolling(load, 3000);

  return (
    <div>
      <TenderNav tender={tender} />
      {schema ? (
        <SchemaReviewPanel tenderId={id} schema={schema} />
      ) : (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">
          {tender?.status === "FAILED"
            ? "Schema compilation failed. Check worker logs and API keys, then re-upload the tender."
            : "Schema is being compiled from the tender document… this page will refresh automatically."}
        </div>
      )}
    </div>
  );
}
