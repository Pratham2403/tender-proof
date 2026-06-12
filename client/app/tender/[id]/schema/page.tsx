"use client";

import { useCallback, useState } from "react";
import { useParams } from "next/navigation";
import type { EvaluationSchema, Tender } from "@/types";
import { api } from "@/lib/api";
import { usePolling } from "@/lib/usePolling";
import { IconAlert, Spinner } from "@/components/ui/icons";
import { Alert, Card } from "@/components/ui/primitives";
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
    <div className="animate-fade-up">
      <TenderNav tender={tender} />
      {schema ? (
        <SchemaReviewPanel tenderId={id} schema={schema} />
      ) : tender?.status === "FAILED" ? (
        <Alert tone="error" className="flex items-start gap-3 p-6">
          <IconAlert className="mt-0.5 h-5 w-5 shrink-0 text-rose-500" />
          <div>
            <p className="text-sm font-semibold text-rose-900">
              Schema compilation failed
            </p>
            <p className="mt-1 text-sm text-rose-700/80">
              Check the worker logs and API keys, then re-upload the tender
              from the dashboard.
            </p>
          </div>
        </Alert>
      ) : (
        <Card className="flex flex-col items-center justify-center px-8 py-16 text-center">
          <Spinner className="h-6 w-6 text-indigo-600" />
          <p className="mt-4 text-sm font-semibold text-slate-700">
            Compiling eligibility schema
          </p>
          <p className="mt-1 max-w-sm text-sm text-slate-500">
            The tender document is being read and structured into typed
            criteria. This page refreshes automatically.
          </p>
        </Card>
      )}
    </div>
  );
}
