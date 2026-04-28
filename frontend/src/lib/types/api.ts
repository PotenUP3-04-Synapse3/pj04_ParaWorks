// ============================================================
// TypeScript 타입 — FastAPI Pydantic 스키마 1:1 매핑
// ============================================================

// ── 공통 ────────────────────────────────────────────────────
export type UUID = string;
export type ISODateString = string;

export type ReviewStatus = 'pending' | 'confirmed' | 'rejected' | 'archived';
export type PermissionLevel = 'public' | 'team' | 'department' | 'restricted' | 'confidential';
export type UserRole = 'admin' | 'manager' | 'member' | 'viewer';
export type AssetType = 'document' | 'decision' | 'process' | 'pattern' | 'template' | 'faq' | 'other';
export type ProjectStatus = 'active' | 'completed' | 'archived';
export type IntegrationType = 'google_drive' | 'gmail' | 'slack' | 'google_calendar';
export type IntegrationStatus = 'connected' | 'disconnected' | 'error' | 'syncing';
export type NotificationType =
  | 'review_request'
  | 'sync_complete'
  | 'sync_error'
  | 'hitl_approval'
  | 'handover_request'
  | 'system';

// ── Auth ────────────────────────────────────────────────────
export interface LoginRequest {
  email: string;
  password: string;
}

export interface UserRead {
  id: UUID;
  email: string;
  display_name: string;
  role: UserRole;
  organization_id: UUID;
  department_id: UUID | null;
  team_id: UUID | null;
  is_active: boolean;
  created_at: ISODateString;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface LoginResponse extends TokenResponse {
  user: UserRead;
}

// ── Search ──────────────────────────────────────────────────
export interface SourceSnippet {
  source_id: UUID;
  title: string;
  url: string | null;
  snippet: string;
  score: number;
}

export interface SearchRequest {
  query: string;
  org_id: UUID;
  user_id: UUID;
  top_k?: number;
  filters?: Record<string, unknown>;
}

export interface SearchResponse {
  answer: string;
  sources: SourceSnippet[];
  confidence_score: number;
  timeline_events: TimelineEvent[];
  related_decisions: DecisionSummary[];
}

// ── Timeline ─────────────────────────────────────────────────
export interface TimelineEvent {
  id: UUID;
  occurred_at: ISODateString;
  source_type: 'google_drive' | 'gmail' | 'slack' | 'google_calendar' | 'decision' | 'manual';
  title: string;
  summary: string | null;
  url: string | null;
  actor_name: string | null;
  metadata: Record<string, unknown>;
}

// ── Decision Records ─────────────────────────────────────────
export interface DecisionSummary {
  id: UUID;
  title: string;
  decision_maker: string;
  decided_at: ISODateString | null;
  confidence_score: number;
  review_status: ReviewStatus;
  permission_level: PermissionLevel;
}

export interface DecisionRecordRead extends DecisionSummary {
  summary: string | null;
  rationale: string | null;
  alternatives_considered: string[] | null;
  constraints: string[] | null;
  stakeholders: string[] | null;
  source_links: string[];
  source_snippets: SourceSnippet[];
  related_project_id: UUID | null;
  created_at: ISODateString;
  updated_at: ISODateString;
}

export interface DecisionRecordCreate {
  title: string;
  summary?: string;
  rationale?: string;
  decision_maker: string;
  decided_at?: ISODateString;
  alternatives_considered?: string[];
  constraints?: string[];
  stakeholders?: string[];
  source_links?: string[];
  permission_level?: PermissionLevel;
  related_project_id?: UUID;
}

export interface DecisionRecordUpdate {
  title?: string;
  summary?: string;
  rationale?: string;
  decision_maker?: string;
  decided_at?: ISODateString;
  alternatives_considered?: string[];
  constraints?: string[];
  stakeholders?: string[];
  source_links?: string[];
  permission_level?: PermissionLevel;
  review_status?: ReviewStatus;
  related_project_id?: UUID;
}

// ── Knowledge Assets ─────────────────────────────────────────
export interface KnowledgeAssetRead {
  id: UUID;
  title: string;
  asset_type: AssetType;
  content: string | null;
  tags: string[];
  permission_level: PermissionLevel;
  review_status: ReviewStatus;
  confidence_score: number;
  source_links: string[];
  related_decisions: UUID[];
  created_at: ISODateString;
  updated_at: ISODateString;
}

// ── Projects ─────────────────────────────────────────────────
export interface ProjectRead {
  id: UUID;
  organization_id: UUID;
  name: string;
  description: string | null;
  status: ProjectStatus;
  owner_id: UUID | null;
  department_id: UUID | null;
  started_at: ISODateString | null;
  ended_at: ISODateString | null;
  created_at: ISODateString;
  updated_at: ISODateString;
}

export interface ProjectCreate {
  name: string;
  description?: string;
  status?: ProjectStatus;
  owner_id?: UUID;
  department_id?: UUID;
  started_at?: ISODateString;
  ended_at?: ISODateString;
}

export interface ProjectUpdate {
  name?: string;
  description?: string;
  status?: ProjectStatus;
  owner_id?: UUID;
  department_id?: UUID;
  started_at?: ISODateString;
  ended_at?: ISODateString;
}

// ── Notifications ────────────────────────────────────────────
export interface NotificationRead {
  id: UUID;
  organization_id: UUID;
  user_id: UUID;
  type: NotificationType;
  title: string;
  body: string | null;
  link: string | null;
  is_read: boolean;
  payload: Record<string, unknown>;
  created_at: ISODateString;
}

// ── Integrations ─────────────────────────────────────────────
export interface IntegrationStatusRead {
  id: UUID;
  organization_id: UUID;
  type: IntegrationType;
  status: IntegrationStatus;
  last_synced_at: ISODateString | null;
  next_sync_at: ISODateString | null;
  error_message: string | null;
  created_at: ISODateString;
  updated_at: ISODateString;
}

// ── Admin / Audit ─────────────────────────────────────────────
export interface AuditLogRead {
  id: UUID;
  organization_id: UUID;
  actor_id: UUID | null;
  actor_email: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  detail: string | null;
  ip_address: string | null;
  created_at: ISODateString;
}

// ── Knowledge Map (React Flow) ───────────────────────────────
export interface KnowledgeMapNode {
  id: string;
  type: 'decision' | 'knowledge_asset' | 'document';
  position: { x: number; y: number };
  data: {
    label: string;
    review_status?: ReviewStatus;
    permission_level?: PermissionLevel;
    [key: string]: unknown;
  };
}

export interface KnowledgeMapEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
}

export interface KnowledgeMapData {
  nodes: KnowledgeMapNode[];
  edges: KnowledgeMapEdge[];
}

// ── SSE 이벤트 ───────────────────────────────────────────────
export type SSEEventType = 'connected' | 'progress' | 'done' | 'error';

export interface SSEEvent {
  type: SSEEventType;
  job_id?: string;
  pct?: number;
  message?: string;
}

// ── API 오류 ─────────────────────────────────────────────────
export interface ApiError {
  status: number;
  detail: string;
}

// ── Handover ─────────────────────────────────────────────────
export interface HandoverPacketRead {
  id: UUID;
  from_user_id: UUID;
  to_user_id: UUID;
  summary: string;
  decisions: DecisionSummary[];
  knowledge_assets: KnowledgeAssetRead[];
  created_at: ISODateString;
}
