import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook } from '@testing-library/react'
import { waitFor } from '@testing-library/dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useOrganizations, usePlanTypes, useConvertPlan } from './useOrganizations'
import * as api from '../api/organizations'

// Mock the API
vi.mock('../api/organizations')

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('useOrganizations', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should fetch organizations', async () => {
    const mockData = {
      organizations: [
        {
          id: 1,
          name: 'Test Org',
          industry: null,
          stripe_customer_id: null,
          stripe_subscription_id: null,
          bot_count: 1,
          current_usage: 100,
          bonus_answers: 50,
        },
      ],
      total: 1,
      page: 1,
      limit: 25,
    }

    vi.mocked(api.fetchOrganizations).mockResolvedValue(mockData)

    const { result } = renderHook(() => useOrganizations(1, 25), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(mockData)
  })

  it('should handle fetch error', async () => {
    vi.mocked(api.fetchOrganizations).mockRejectedValue(new Error('Network error'))

    const { result } = renderHook(() => useOrganizations(1, 25), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(result.current.error).toBeTruthy()
  })
})

describe('usePlanTypes', () => {
  it('should fetch plan types for organizations', async () => {
    const mockData = [
      { organization_id: 1, plan_type: 'Free' as const, plan_limits: null },
      { organization_id: 2, plan_type: 'Starter' as const, plan_limits: null },
    ]

    vi.mocked(api.fetchPlanTypes).mockResolvedValue(mockData)

    const { result } = renderHook(() => usePlanTypes([1, 2]), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(mockData)
  })

  it('should not fetch when orgIds is empty', () => {
    const { result } = renderHook(() => usePlanTypes([]), {
      wrapper: createWrapper(),
    })

    expect(result.current.fetchStatus).toBe('idle')
  })
})

describe('useConvertPlan', () => {
  it('should convert organization plan', async () => {
    vi.mocked(api.convertOrganizationPlan).mockResolvedValue({
      success: true,
      subscription_id: 'sub_123',
    })

    const { result } = renderHook(() => useConvertPlan(), {
      wrapper: createWrapper(),
    })

    result.current.mutate({ orgId: 1, planType: 'Team' })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(api.convertOrganizationPlan).toHaveBeenCalledWith(1, 'Team')
  })
})
