import { apiRequest } from './client'
import type {
  OrganizationsResponse,
  OrganizationPlanInfo,
  PlanType,
  SearchOrganizationsResponse,
} from '../types/organization'

export async function fetchOrganizations(
  page: number = 1,
  limit: number = 25
): Promise<OrganizationsResponse> {
  return apiRequest<OrganizationsResponse>(
    `/api/organizations?page=${page}&limit=${limit}`
  )
}

export async function fetchPlanTypes(orgIds: number[]): Promise<OrganizationPlanInfo[]> {
  const idsParam = orgIds.join(',')
  return apiRequest<OrganizationPlanInfo[]>(`/api/plan-types?org_ids=${idsParam}`)
}

export async function convertOrganizationPlan(
  orgId: number,
  planType: PlanType
): Promise<{ success: boolean; subscription_id?: string; error?: string }> {
  const endpoint = {
    'Design Partner': '/api/convert-to-design-partner',
    Free: '/api/convert-to-free-plan',
    Starter: '/api/convert-to-starter-plan',
    Team: '/api/convert-to-team-plan',
    Unknown: '',
  }[planType]

  if (!endpoint) {
    throw new Error(`Invalid plan type: ${planType}`)
  }

  return apiRequest(endpoint, {
    method: 'POST',
    body: JSON.stringify({ organization_id: orgId }),
  })
}

export async function searchOrganizations(
  query: string,
  limit: number = 50
): Promise<SearchOrganizationsResponse> {
  if (query.length < 2) {
    return { organizations: [], total_matches: 0, query }
  }

  return apiRequest<SearchOrganizationsResponse>(
    `/api/organizations/search?q=${encodeURIComponent(query)}&limit=${limit}`
  )
}
