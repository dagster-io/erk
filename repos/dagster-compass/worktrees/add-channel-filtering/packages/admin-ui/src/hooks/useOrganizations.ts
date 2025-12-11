import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchOrganizations,
  fetchPlanTypes,
  convertOrganizationPlan,
} from '../api/organizations'
import type { PlanType } from '../types/organization'

export function useOrganizations(page: number, limit: number) {
  return useQuery({
    queryKey: ['organizations', page, limit],
    queryFn: () => fetchOrganizations(page, limit),
  })
}

export function usePlanTypes(orgIds: number[]) {
  return useQuery({
    queryKey: ['planTypes', orgIds],
    queryFn: () => fetchPlanTypes(orgIds),
    enabled: orgIds.length > 0,
  })
}

export function useConvertPlan() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ orgId, planType }: { orgId: number; planType: PlanType }) =>
      convertOrganizationPlan(orgId, planType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organizations'] })
      queryClient.invalidateQueries({ queryKey: ['planTypes'] })
    },
  })
}
