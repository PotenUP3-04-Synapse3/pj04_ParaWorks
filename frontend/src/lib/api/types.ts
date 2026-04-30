export type SyncJob = {
  job_id: string;
  connector_type: string;
  status: string;
  message: string;
  progress_pct: number;
};

export type DashboardResponse = {
  source_counts: Record<string, number>;
  pending_review_count: number;
  recent_jobs: SyncJob[];
};

export type ReviewItem = {
  id: number;
  item_type: string;
  payload: Record<string, unknown>;
  source_links: string[];
  source_snippets: string[];
  confidence_score: number;
  permission_level: string;
  status: string;
};

export type ReviewResponse = {
  items: ReviewItem[];
};

export type SearchResult = {
  id: number;
  text: string;
  source_snippet: string;
  source_url?: string | null;
  source_type?: string | null;
  permission_level: string;
};

export type SearchResponse = {
  results: SearchResult[];
  permission_notice?: string;
};

export type IntegrationSyncResponse = {
  job_id: string;
  connector_type: string;
  status: string;
  created_review_items: number;
};
