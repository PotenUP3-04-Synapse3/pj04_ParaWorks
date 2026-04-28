import { apiFetch, apiPost, apiPatch } from './client';
import type {
  DecisionRecordRead,
  DecisionSummary,
  DecisionRecordCreate,
  DecisionRecordUpdate,
  UUID,
} from '@/lib/types/api';

export const decisionsApi = {
  list: (orgId: UUID, params?: { skip?: number; limit?: number; review_status?: string }) =>
    apiFetch<DecisionSummary[]>('decisions', {
      searchParams: { org_id: orgId, ...params },
    }),

  get: (id: UUID) => apiFetch<DecisionRecordRead>(`decisions/${id}`),

  create: (body: DecisionRecordCreate) => apiPost<DecisionRecordRead>('decisions', body),

  update: (id: UUID, body: DecisionRecordUpdate) =>
    apiPatch<DecisionRecordRead>(`decisions/${id}`, body),
};
