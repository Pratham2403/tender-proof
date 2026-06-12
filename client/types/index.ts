// Shared TypeScript types mirroring backend Pydantic schemas

export type TenderStatus =
  | "UPLOADING"
  | "COMPILING"
  | "PENDING_APPROVAL"
  | "APPROVED"
  | "EVALUATING"
  | "COMPLETE"
  | "FAILED";

export type BidderStatus =
  | "QUEUED"
  | "EXTRACTING"
  | "EVALUATING"
  | "EVALUATED"
  | "FAILED";

export type Verdict = "PASS" | "FAIL" | "REVIEW";

export type CriterionType =
  | "CurrencyThreshold"
  | "CountMinimum"
  | "BooleanPresence"
  | "DateRange"
  | "SimilarityScore";

export interface Criterion {
  criterion_id: string;
  label: string;
  criterion_type: CriterionType;
  mandatory: boolean;
  params: Record<string, unknown>;
  accepted_evidence: string[];
  source_text: string;
}

export interface Tender {
  tender_id: string;
  title: string;
  status: TenderStatus;
  created_at: string;
  bidder_count: number;
}

export interface EvaluationSchema {
  schema_id: string;
  tender_id: string;
  criteria: Criterion[];
  status: "PENDING_APPROVAL" | "APPROVED";
  approved_by: string | null;
  approved_at: string | null;
  compiled_at: string;
}

export interface Bidder {
  bidder_id: string;
  tender_id: string;
  company_name: string;
  file_names: string[];
  status: BidderStatus;
  submitted_at: string;
}

export interface CriterionVerdict {
  criterion_id: string;
  label: string;
  mandatory: boolean;
  verdict: Verdict;
  extracted_value: string | null;
  document_name: string | null;
  page_number: number | null;
  reason: string;
  confidence: number;
  rule_applied: string | null;
  override_by: string | null;
}

export interface BidderSummary {
  bidder_id: string;
  company_name: string;
  overall_verdict: Verdict;
  criteria_verdicts: CriterionVerdict[];
}

export interface ConsolidatedReport {
  tender_id: string;
  bidder_summaries: BidderSummary[];
}

export interface ReviewItem {
  item_id: string;
  bidder_id: string;
  company_name: string;
  criterion_id: string;
  label: string;
  mandatory: boolean;
  extracted_value: string | null;
  document_name: string | null;
  page_number: number | null;
  raw_text: string | null;
  reason: string;
  confidence: number;
  created_at: string;
}

export interface JobStatus {
  job_id: string;
  status: string;
  progress_pct: number;
  message: string;
  result?: unknown;
}

export interface JobProgressEvent {
  type: "progress" | "complete" | "error" | "status";
  pct?: number;
  message?: string;
  reason?: string;
  state?: string;
}
