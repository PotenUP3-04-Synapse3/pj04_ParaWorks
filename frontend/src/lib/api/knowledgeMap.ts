import { apiFetch } from './client';
import type { KnowledgeMapData, UUID } from '@/lib/types/api';

export const knowledgeMapApi = {
  get: (orgId: UUID, depth = 2) =>
    apiFetch<KnowledgeMapData>('knowledge-map', {
      searchParams: { org_id: orgId, depth },
    }),
};
