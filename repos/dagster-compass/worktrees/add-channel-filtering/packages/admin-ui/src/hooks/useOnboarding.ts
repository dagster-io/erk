import { useQuery } from '@tanstack/react-query'
import { fetchOnboardingStates, fetchOnboardingDetails } from '../api/onboarding'

export function useOnboardingStates(limit: number = 100) {
  return useQuery({
    queryKey: ['onboarding', limit],
    queryFn: () => fetchOnboardingStates(limit),
  })
}

export function useOnboardingDetails(orgId: number | null) {
  return useQuery({
    queryKey: ['onboarding', orgId, 'details'],
    queryFn: () => fetchOnboardingDetails(orgId!),
    enabled: orgId !== null,
  })
}
