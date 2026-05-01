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

export type ReviewStatus =
  | "pending_review"
  | "approved"
  | "rejected"
  | "needs_more_evidence";

export type ReviewItemUpdate = {
  payload?: Record<string, unknown>;
  source_links?: string[];
  source_snippets?: string[];
  confidence_score?: number;
  permission_level?: string;
};

export type ReviewItem = {
  id: number;
  item_type: string;
  payload: Record<string, unknown>;
  source_links: string[];
  source_snippets: string[];
  confidence_score: number;
  permission_level: string;
  status: ReviewStatus;
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

export type AgentReviewResponse = {
  agent_name: string;
  status: string;
  created_review_items: number;
};

export type SlackAgentReviewResponse = AgentReviewResponse;

export type MessageChannel = {
  id: string;
  name: string;
  description: string;
  unread_count: number;
};

export type Message = {
  id: string;
  channel_id: string;
  author_name: string;
  author_role: string;
  body: string;
  created_at: string;
};

export type MessageChannelsResponse = {
  channels: MessageChannel[];
};

export type ChannelMessagesResponse = {
  channel: MessageChannel;
  messages: Message[];
};
