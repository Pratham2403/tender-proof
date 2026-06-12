"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useJobProgress } from "@/lib/ws";

export function TenderUpload({ onCreated }: { onCreated?: () => void }) {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [tenderId, setTenderId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const progress = useJobProgress(jobId);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !title.trim()) return;
    setError(null);
    setSubmitting(true);
    try {
      const res = await api.createTender(title.trim(), file);
      setJobId(res.job_id);
      setTenderId(res.tender_id);
      onCreated?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setSubmitting(false);
    }
  };

  if (jobId) {
    if (progress?.type === "complete") {
      router.push(`/tender/${tenderId}/schema`);
    }
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-6">
        {progress?.type === "error" ? (
          <p className="text-sm text-rose-600">
            Schema compilation failed: {progress.reason}
          </p>
        ) : (
          <div>
            <p className="mb-2 text-sm font-medium text-slate-700">
              Compiling eligibility schema with Gemini Flash…
            </p>
            <div className="h-2 overflow-hidden rounded-full bg-slate-200">
              <div
                className="h-full bg-indigo-500 transition-all"
                style={{ width: `${progress?.pct ?? 5}%` }}
              />
            </div>
            <p className="mt-2 text-xs text-slate-500">
              {progress?.message ?? "Waiting for worker…"}
            </p>
          </div>
        )}
      </div>
    );
  }

  return (
    <form
      onSubmit={submit}
      className="rounded-xl border border-slate-200 bg-white p-6"
    >
      <h2 className="mb-4 text-base font-semibold">Upload a new tender</h2>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
        <label className="flex-1 text-sm">
          <span className="mb-1 block font-medium text-slate-700">Title</span>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. CRPF Construction Tender 2025"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
            required
          />
        </label>
        <label className="flex-1 text-sm">
          <span className="mb-1 block font-medium text-slate-700">
            Tender document (PDF / DOCX)
          </span>
          <input
            type="file"
            accept=".pdf,.docx,.doc"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="w-full text-sm text-slate-500 file:mr-3 file:rounded-lg file:border-0 file:bg-indigo-50 file:px-3 file:py-2 file:text-sm file:font-medium file:text-indigo-700 hover:file:bg-indigo-100"
            required
          />
        </label>
        <button
          type="submit"
          disabled={submitting || !file || !title.trim()}
          className="rounded-lg bg-indigo-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {submitting ? "Uploading…" : "Upload & compile"}
        </button>
      </div>
      {error && <p className="mt-3 text-sm text-rose-600">{error}</p>}
    </form>
  );
}
