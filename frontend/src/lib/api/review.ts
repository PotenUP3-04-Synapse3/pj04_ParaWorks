import { apiFetch, apiPost } from './client';
import type { DecisionRecordRead, UUID } from '@/lib/types/api';

export interface ReviewItemRead {
  id: UUID;
  review_status: string;
  title: string;
  summary: string | null;
  confidence_score: number;
  source_links: string[];
  created_at: string;
}

export const reviewApi = {
  list: (orgId: UUID, status = 'pending') =>
    apiFetch<ReviewItemRead[]>('review', {
      searchParams: { org_id: orgId, status },
    }),

  approve: (id: UUID) => apiPost<DecisionRecordRead>(`review/${id}/approve`, {}),

  reject: (id: UUID) => apiPost<DecisionRecordRead>(`review/${id}/reject`, {}),

  edit: (id: UUID, body: Partial<DecisionRecordRead>) =>
    apiPost<DecisionRecordRead>(`review/${id}`, body),
};
