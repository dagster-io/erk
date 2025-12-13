import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook } from '@testing-library/react'
import { waitFor } from '@testing-library/dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useTokens, useCreateToken } from './useTokens'
import * as api from '../api/tokens'

vi.mock('../api/tokens')

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

describe('useTokens', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should fetch tokens', async () => {
    const mockData = {
      tokens: [
        {
          id: 1,
          token: 'test-token',
          created_at: '2024-01-01',
          consumed_at: null,
          is_single_use: false,
          consumer_bonus_answers: 150,
          consumed_by_organization_ids: [],
          organization_name: null,
          organization_id: null,
        },
      ],
    }

    vi.mocked(api.fetchTokens).mockResolvedValue(mockData)

    const { result } = renderHook(() => useTokens(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(mockData)
  })
})

describe('useCreateToken', () => {
  it('should create token', async () => {
    vi.mocked(api.createToken).mockResolvedValue({
      success: true,
      token: 'new-token',
    })

    const { result } = renderHook(() => useCreateToken(), {
      wrapper: createWrapper(),
    })

    result.current.mutate({
      token: 'custom-token',
      is_single_use: false,
      consumer_bonus_answers: 150,
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(api.createToken).toHaveBeenCalledWith({
      token: 'custom-token',
      is_single_use: false,
      consumer_bonus_answers: 150,
    })
  })
})
