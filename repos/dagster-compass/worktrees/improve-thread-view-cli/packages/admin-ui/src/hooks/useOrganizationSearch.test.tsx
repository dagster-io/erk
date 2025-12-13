import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook } from '@testing-library/react'
import { waitFor } from '@testing-library/dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useOrganizationSearch } from './useOrganizationSearch'
import * as api from '../api/organizations'

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

describe('useOrganizationSearch', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should not search when query < 2 characters', async () => {
    const { result } = renderHook(() => useOrganizationSearch('a', true), {
      wrapper: createWrapper(),
    })

    // Wait a bit to ensure debounce completes
    await waitFor(() => new Promise((resolve) => setTimeout(resolve, 400)))

    expect(result.current.fetchStatus).toBe('idle')
    expect(api.searchOrganizations).not.toHaveBeenCalled()
  })

  it('should search when query >= 2 characters', async () => {
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
      total_matches: 1,
      query: 'test',
    }

    vi.mocked(api.searchOrganizations).mockResolvedValue(mockData)

    const { result } = renderHook(() => useOrganizationSearch('test', true), {
      wrapper: createWrapper(),
    })

    // Wait for debounce (300ms) + query execution
    await waitFor(
      () => {
        expect(result.current.isSuccess).toBe(true)
      },
      { timeout: 1000 }
    )

    expect(api.searchOrganizations).toHaveBeenCalledWith('test', 50)
    expect(result.current.data).toEqual(mockData)
  })

  it('should debounce search query', async () => {
    const { rerender } = renderHook(({ query }) => useOrganizationSearch(query, true), {
      wrapper: createWrapper(),
      initialProps: { query: 'te' },
    })

    // Rapidly change query
    rerender({ query: 'tes' })
    rerender({ query: 'test' })

    // Should only call API once after debounce completes
    await waitFor(
      () => {
        expect(api.searchOrganizations).toHaveBeenCalledTimes(1)
      },
      { timeout: 1000 }
    )

    expect(api.searchOrganizations).toHaveBeenCalledWith('test', 50)
  })

  it('should not search when disabled', async () => {
    const { result } = renderHook(() => useOrganizationSearch('test', false), {
      wrapper: createWrapper(),
    })

    await waitFor(() => new Promise((resolve) => setTimeout(resolve, 400)))

    expect(result.current.fetchStatus).toBe('idle')
    expect(api.searchOrganizations).not.toHaveBeenCalled()
  })
})
