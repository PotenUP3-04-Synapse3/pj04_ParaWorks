import { apiFetch, apiPost } from './client';
import type { SearchRequest, SearchResponse } from '@/lib/types/api';

export const searchApi = {
  query: (body: SearchRequest) => apiPost<SearchResponse>('search', body),
};
