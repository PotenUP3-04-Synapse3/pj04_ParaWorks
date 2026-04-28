import { apiFetch, apiPost, apiPatch, apiDelete } from './client';
import type {
  ProjectRead,
  ProjectCreate,
  ProjectUpdate,
  TimelineEvent,
  DecisionRecordRead,
  UUID,
} from '@/lib/types/api';

export interface ProjectHistoryItem {
  id: UUID;
  title: string;
  occurred_at: string;
  event_type: string;
  diff_from_previous: string | null;
}

export const projectsApi = {
  list: (orgId: UUID, params?: { skip?: number; limit?: number }) =>
    apiFetch<ProjectRead[]>('projects', {
      searchParams: { org_id: orgId, ...params },
    }),

  get: (id: UUID) => apiFetch<ProjectRead>(`projects/${id}`),

  create: (body: ProjectCreate & { organization_id: UUID }) =>
    apiPost<ProjectRead>('projects', body),

  update: (id: UUID, body: ProjectUpdate) =>
    apiPatch<ProjectRead>(`projects/${id}`, body),

  timeline: (id: UUID, params?: { from_date?: string; to_date?: string; source_type?: string }) =>
    apiFetch<TimelineEvent[]>(`projects/${id}/timeline`, {
      searchParams: params ?? {},
    }),

  history: (id: UUID) =>
    apiFetch<ProjectHistoryItem[]>(`projects/${id}/history`),

  decisions: (id: UUID) =>
    apiFetch<DecisionRecordRead[]>(`decisions`, {
      searchParams: { project_id: id },
    }),
};
