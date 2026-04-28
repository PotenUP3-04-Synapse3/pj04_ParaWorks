import { apiFetch, apiPost, apiDelete } from './client';
import type { IntegrationStatusRead, IntegrationType, UUID } from '@/lib/types/api';

export interface SyncJobResponse {
  job_id: string;
  message: string;
}

export const integrationsApi = {
  list: (orgId: UUID) =>
    apiFetch<IntegrationStatusRead[]>('integrations', {
      searchParams: { org_id: orgId },
    }),

  sync: (type: IntegrationType) =>
    apiPost<SyncJobResponse>(`integrations/${type}/sync`, {}),

  disconnect: (type: IntegrationType) =>
    apiDelete(`integrations/${type}`),
};
