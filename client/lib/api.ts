import type {
  Bidder,
  ConsolidatedReport,
  Criterion,
  EvaluationSchema,
  JobStatus,
  ReviewItem,
  Tender,
  Verdict,
} from "@/types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // non-JSON error body — keep statusText
    }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  listTenders: () => request<Tender[]>("/api/tenders"),

  getTender: (tenderId: string) => request<Tender>(`/api/tenders/${tenderId}`),

  createTender: (title: string, file: File) => {
    const form = new FormData();
    form.append("title", title);
    form.append("file", file);
    return request<{ tender_id: string; job_id: string }>("/api/tenders", {
      method: "POST",
      body: form,
    });
  },

  getSchema: (tenderId: string) =>
    request<EvaluationSchema>(`/api/tenders/${tenderId}/schema`),

  approveSchema: (tenderId: string, criteria?: Criterion[]) =>
    request<{ schema_id: string; approved_at: string }>(
      `/api/tenders/${tenderId}/schema`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(
          criteria
            ? { action: "edit_and_approve", criteria }
            : { action: "approve" },
        ),
      },
    ),

  listBidders: (tenderId: string) =>
    request<Bidder[]>(`/api/tenders/${tenderId}/bidders`),

  createBidder: (tenderId: string, companyName: string, files: File[]) => {
    const form = new FormData();
    form.append("company_name", companyName);
    for (const f of files) form.append("files", f);
    return request<{ bidder_id: string; job_id: string }>(
      `/api/tenders/${tenderId}/bidders`,
      { method: "POST", body: form },
    );
  },

  getReport: (tenderId: string) =>
    request<ConsolidatedReport>(`/api/tenders/${tenderId}/report`),

  getReviewQueue: (tenderId: string) =>
    request<ReviewItem[]>(`/api/tenders/${tenderId}/review`),

  resolveReviewItem: (
    tenderId: string,
    itemId: string,
    verdict: Verdict,
    reason: string,
    action: "confirm" | "override" = "confirm",
  ) =>
    request(`/api/tenders/${tenderId}/review/${itemId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, verdict, reason }),
    }),

  getJobStatus: (jobId: string) =>
    request<JobStatus>(`/api/jobs/${jobId}/status`),
};
