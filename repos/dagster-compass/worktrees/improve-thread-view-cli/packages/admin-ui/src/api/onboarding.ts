import { apiRequest } from './client'
import type { OnboardingResponse, OnboardingDetails } from '../types/onboarding'

export async function fetchOnboardingStates(limit: number = 100): Promise<OnboardingResponse> {
  return apiRequest<OnboardingResponse>(`/api/onboarding?limit=${limit}`)
}

export async function fetchOnboardingDetails(orgId: number): Promise<OnboardingDetails> {
  return apiRequest<OnboardingDetails>(`/api/onboarding/${orgId}/details`)
}
