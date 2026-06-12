"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useJobProgress } from "@/lib/ws";
import { Button, Card, ProgressBar } from "@/components/ui/primitives";
import { FileDrop } from "@/components/ui/FileDrop";
import { IconAlert, Spinner } from "@/components/ui/icons";
import { useToast } from "@/components/ui/toast";

export function TenderUpload({ onCreated }: { onCreated?: () => void }) {
  const router = useRouter();
  const toast = useToast();
  const [title, setTitle] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [jobId, setJobId] = useState<string | null>(null);
  const [tenderId, setTenderId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const progress = useJobProgress(jobId);

  useEffect(() => {
    if (progress?.type === "complete" && tenderId) {
      toast("success", "Eligibility schema compiled — ready for your review.");
      router.push(`/tender/${tenderId}/schema`);
    }
  }, [progress, tenderId, router, toast]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (files.length === 0 || !title.trim()) return;
    setSubmitting(true);
    try {
      const res = await api.createTender(title.trim(), files[0]);
      setJobId(res.job_id);
      setTenderId(res.tender_id);
      onCreated?.();
    } catch (err) {
      toast("error", err instanceof Error ? err.message : "Upload failed");
      setSubmitting(false);
    }
  };

  if (jobId) {
    return (
      <Card className="p-6">
        {progress?.type === "error" ? (
          <div className="flex items-start gap-3">
            <IconAlert className="mt-0.5 h-5 w-5 shrink-0 text-rose-500" />
            <div>
              <p className="text-sm font-semibold text-slate-800">
                Schema compilation failed
              </p>
              <p className="mt-1 text-sm text-slate-500">{progress.reason}</p>
            </div>
          </div>
        ) : (
          <div>
            <div className="flex items-center gap-2.5">
              <Spinner className="h-4 w-4 text-indigo-600" />
              <p className="text-sm font-semibold text-slate-800">
                Compiling eligibility schema
              </p>
            </div>
            <p className="mb-3 mt-1 text-sm text-slate-500">
              Gemini Flash is reading the tender and structuring every
              eligibility criterion. You&apos;ll review the result before any
              evaluation begins.
            </p>
            <ProgressBar value={progress?.pct ?? 5} />
            <p className="mt-2 text-xs text-slate-400">
              {progress?.message ?? "Waiting for worker…"}
            </p>
          </div>
        )}
      </Card>
    );
  }

  return (
    <Card className="p-6">
      <h2 className="text-[15px] font-semibold text-slate-900">
        New tender evaluation
      </h2>
      <p className="mt-0.5 text-sm text-slate-500">
        Upload the tender document; eligibility criteria are extracted into a
        typed schema for your approval.
      </p>
      <form onSubmit={submit} className="mt-5 space-y-4">
        <label className="block text-sm">
          <span className="mb-1.5 block font-medium text-slate-700">
            Tender title
          </span>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. CRPF Construction Services 2025 — NIT 017"
            className="w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2.5 text-sm shadow-sm outline-none transition-shadow placeholder:text-slate-400 focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100"
            required
          />
        </label>
        <FileDrop
          files={files}
          onChange={setFiles}
          accept=".pdf,.docx,.doc"
          hint="PDF or DOCX · up to 50 MB"
        />
        <div className="flex justify-end">
          <Button
            type="submit"
            loading={submitting}
            disabled={files.length === 0 || !title.trim()}
          >
            Upload & compile schema
          </Button>
        </div>
      </form>
    </Card>
  );
}
