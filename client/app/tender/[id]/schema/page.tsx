"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import type { EvaluationSchema, Tender } from "@/types";
import { api } from "@/lib/api";
import { TenderNav } from "@/components/TenderNav";
import { SchemaReviewPanel } from "@/components/schema/SchemaReviewPanel";

export default function SchemaPage() {
  const { id } = useParams<{ id: string }>();
  const [tender, setTender] = useState<Tender | null>(null);
  const [schema, setSchema] = useState<EvaluationSchema | null>(null);
  const [waiting, setWaiting] = useState(false);

  const load = useCallback(async () => {
    const t = await api.getTender(id);
    setTender(t);
    try {
      setSchema(await api.getSchema(id));
      setWaiting(false);
    } catch {
      // Schema not compiled yet — keep polling while the worker runs
      setWaiting(true);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!waiting) return;
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, [waiting, load]);

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
