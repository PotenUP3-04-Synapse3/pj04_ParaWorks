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

export type AgentRunAgentSummary = {
  agent_name: string;
  run_count: number;
  total_tokens: number;
  estimated_cost_usd: number;
  average_tokens_per_run: number;
  latest_run_id: number;
  latest_status: string;
};

export type AgentRunSummaryResponse = {
  totals: {
    total_runs: number;
    total_tokens: number;
    estimated_cost_usd: number;
    average_tokens_per_run: number;
    average_cost_per_run: number;
    cache_hits: number;
    cache_hit_rate: number;
  };
  by_status: Record<string, number>;
  by_agent: AgentRunAgentSummary[];
};

export type OrchestrationStatusResponse = {
  workflow_name: string;
  backend: string;
  node_names: string[];
  graph_mermaid: string;
  cost_policy: {
    delta_sync: boolean;
    source_hash_skip: boolean;
    evidence_token_budget: boolean;
    per_run_budget_usd?: number;
    budget_actions?: string[];
    paid_llm_calls_in_status_api: boolean;
    requires_explicit_run: boolean;
  };
};

export type OrchestrationDryRunResponse = {
  workflow_name: string;
  backend: string;
  objective: string;
  inputs: Record<string, unknown>;
  completed_nodes: string[];
  outputs: Record<string, string>;
  token_cost_usd: number;
  cost_policy: OrchestrationStatusResponse["cost_policy"];
};

export type RagIndexingJobSummary = {
  job_id: string;
  connector_type: string;
  status: string;
  message: string;
  failure_reason?: string | null;
  progress_pct: number;
  indexed_count: number;
  skipped_count: number;
  saved_embedding_calls: number;
  updated_at: string;
};

export type RagIndexingSummaryResponse = {
  state_counts: Record<string, number>;
  latest_jobs: RagIndexingJobSummary[];
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

export type ReviewPromotionPreview = {
  target_type: string;
  can_approve: boolean;
  missing_required_fields: string[];
  normalized_payload: Record<string, string>;
};

export type ReviewResponse = {
  items: ReviewItem[];
};

export type SearchResult = {
  id: number;
  source_id: string;
  text: string;
  source_snippet: string;
  source_url?: string | null;
  source_type?: string | null;
  permission_level: string;
};

export type SearchResponse = {
  results: SearchResult[];
  hidden_match_count: number;
  permission_notice?: string;
};

export type AskResponse = {
  agent_name: string;
  prompt_version: string;
  question: string;
  answer: string;
  source_ids: string[];
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
  fetched_events: number;
  skipped_events: number;
};

export type IntegrationManifest = {
  type: string;
  display_name: string;
  mode: string;
  status: string;
  auth_type: string;
  required_scopes: string[];
  sync_strategy: string;
  cost_policy: string;
};

export type OAuthInstallUrlResponse = {
  connector_type: string;
  configured: boolean;
  install_url?: string | null;
  state?: string | null;
  required_scopes: string[];
};

export type SlackOAuthInstallUrlResponse = OAuthInstallUrlResponse;

export type IntegrationConnection = {
  connector_type: string;
  workspace_id: string;
  workspace_name: string;
  status: string;
  credential_status?: "available" | "missing";
  masked_bot_token: string;
  scopes: string[];
};

export type AgentReviewResponse = {
  agent_name: string;
  status: string;
  created_review_items: number;
};

export type SlackAgentReviewResponse = AgentReviewResponse;

export type SlackRuntimeStatus = {
  connector_type: "slack";
  mode: "mock" | "live";
  configured_channel_ids: string[];
  connection_status: string;
  credential_status: "available" | "missing";
  latest_sync?: {
    job_id: string;
    status: string;
    message: string;
    progress_pct: number;
  } | null;
  cost_policy: {
    status_lookup_triggers_sync: boolean;
    status_lookup_triggers_llm: boolean;
  };
};

export type GoogleRuntimeStatus = {
  connector_type: "gmail" | "drive" | "calendar";
  mode: "mock" | "live";
  connection_status: string;
  credential_status: "available" | "missing";
  account_name?: string | null;
  latest_sync?: {
    job_id: string;
    status: string;
    message: string;
    progress_pct: number;
  } | null;
  cost_policy: {
    status_lookup_triggers_sync: boolean;
    status_lookup_triggers_llm: boolean;
  };
};

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
