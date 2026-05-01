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

export type AgentRunSummaryItem = {
  id: number;
  agent_name: string;
  prompt_version: string;
  status: string;
  source_window: string;
  cache_key: string;
  model_name: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  token_usage?: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
  };
  estimated_cost_usd: number;
  permission_level: string;
  metadata: Record<string, unknown>;
  started_at: string;
  completed_at?: string | null;
};

export type AgentRunsResponse = {
  total_runs: number;
  total_tokens: number;
  estimated_cost_usd: number;
  recent_runs: AgentRunSummaryItem[];
};

export type KnowledgeItem = {
  id: number;
  title: string;
  summary: string;
  priority?: string;
  source_links: string[];
  source_snippets: string[];
  confidence_score: number;
  permission_level: string;
  review_status: string;
  created_at: string;
};

export type KnowledgeResponse = {
  counts: {
    decisions: number;
    history_events: number;
    todos: number;
  };
  decisions: KnowledgeItem[];
  history_events: KnowledgeItem[];
  todos: KnowledgeItem[];
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

export type AskResponse = {
  agent_name: string;
  prompt_version: string;
  question: string;
  answer: string;
  source_links: string[];
  source_snippets: string[];
  permission_level: string;
  hidden_match_count: number;
  permission_notice?: string | null;
  cache_key: string;
  model_name: string;
  estimated_cost_usd: number;
  token_usage: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
  };
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
