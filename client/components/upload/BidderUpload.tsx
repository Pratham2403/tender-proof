"use client";

import { useState } from "react";
import { api } from "@/lib/api";

export function BidderUpload({
  tenderId,
  onUploaded,
}: {
  tenderId: string;
  onUploaded: () => void;
}) {
  const [companyName, setCompanyName] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!companyName.trim() || files.length === 0) return;
    setError(null);
    setSubmitting(true);
    try {
      await api.createBidder(tenderId, companyName.trim(), files);
      setCompanyName("");
      setFiles([]);
      onUploaded();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form
      onSubmit={submit}
      className="rounded-xl border border-slate-200 bg-white p-6"
    >
      <h2 className="mb-4 text-base font-semibold">
        Upload bidder submission
      </h2>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
        <label className="flex-1 text-sm">
          <span className="mb-1 block font-medium text-slate-700">
            Company name
          </span>
          <input
            type="text"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            placeholder="e.g. Apex Constructions Pvt Ltd"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
            required
          />
        </label>
        <label className="flex-1 text-sm">
          <span className="mb-1 block font-medium text-slate-700">
            Documents (PDF, DOCX, JPG, PNG — multiple allowed)
          </span>
          <input
            type="file"
            multiple
            accept=".pdf,.docx,.doc,.jpg,.jpeg,.png,.webp"
            onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
            className="w-full text-sm text-slate-500 file:mr-3 file:rounded-lg file:border-0 file:bg-indigo-50 file:px-3 file:py-2 file:text-sm file:font-medium file:text-indigo-700 hover:file:bg-indigo-100"
            required
          />
        </label>
        <button
          type="submit"
          disabled={submitting || files.length === 0 || !companyName.trim()}
          className="rounded-lg bg-indigo-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {submitting ? "Uploading…" : "Upload & evaluate"}
        </button>
      </div>
      {files.length > 0 && (
        <p className="mt-2 text-xs text-slate-500">
          {files.length} file(s): {files.map((f) => f.name).join(", ")}
        </p>
      )}
      {error && <p className="mt-3 text-sm text-rose-600">{error}</p>}
    </form>
  );
}
