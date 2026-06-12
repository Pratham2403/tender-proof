"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { Button, Card } from "@/components/ui/primitives";
import { FileDrop } from "@/components/ui/FileDrop";
import { useToast } from "@/components/ui/toast";

export function BidderUpload({
  tenderId,
  onUploaded,
}: {
  tenderId: string;
  onUploaded: () => void;
}) {
  const toast = useToast();
  const [companyName, setCompanyName] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [submitting, setSubmitting] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!companyName.trim() || files.length === 0) return;
    setSubmitting(true);
    try {
      await api.createBidder(tenderId, companyName.trim(), files);
      toast(
        "success",
        `${companyName.trim()} queued — extraction starts immediately.`,
      );
      setCompanyName("");
      setFiles([]);
      onUploaded();
    } catch (err) {
      toast("error", err instanceof Error ? err.message : "Upload failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card className="p-6">
      <h2 className="text-[15px] font-semibold text-slate-900">
        Add bidder submission
      </h2>
      <p className="mt-0.5 text-sm text-slate-500">
        Attach the bidder&apos;s full document package — typed PDFs, scans and
        photographs are all read directly by the vision model.
      </p>
      <form onSubmit={submit} className="mt-5 space-y-4">
        <label className="block text-sm">
          <span className="mb-1.5 block font-medium text-slate-700">
            Company name
          </span>
          <input
            type="text"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            placeholder="e.g. Apex Constructions Pvt Ltd"
            className="w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2.5 text-sm shadow-sm outline-none transition-shadow placeholder:text-slate-400 focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100"
            required
          />
        </label>
        <FileDrop
          files={files}
          onChange={setFiles}
          accept=".pdf,.docx,.doc,.jpg,.jpeg,.png,.webp"
          multiple
          hint="PDF, DOCX, JPG, PNG · multiple files · up to 50 MB each"
        />
        <div className="flex justify-end">
          <Button
            type="submit"
            loading={submitting}
            disabled={files.length === 0 || !companyName.trim()}
          >
            Upload & evaluate
          </Button>
        </div>
      </form>
    </Card>
  );
}
