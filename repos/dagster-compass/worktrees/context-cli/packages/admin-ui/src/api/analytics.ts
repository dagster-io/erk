import { apiRequest } from './client'
import type { AnalyticsResponse } from '../types/analytics'

export async function fetchAnalytics(
  organizationId: number,
  page: number = 1,
  limit: number = 50
): Promise<AnalyticsResponse> {
  return apiRequest<AnalyticsResponse>(
    `/api/analytics?organization_id=${organizationId}&page=${page}&limit=${limit}`
  )
}
