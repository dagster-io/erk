import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook } from '@testing-library/react'
import { waitFor } from '@testing-library/dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useThreadDetail } from './useThreadDetail'
import * as api from '../api/threads'

vi.mock('../api/threads')

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

describe('useThreadDetail', () => {
  const mockThreadDetail = {
    bot_id: 'T123456-test-channel',
    team_id: 'T123456',
    channel_id: 'C123456',
    thread_ts: '1234567890.123456',
    html: '<div>Test thread content</div>',
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should fetch thread detail successfully', async () => {
    vi.mocked(api.fetchThreadDetail).mockResolvedValue(mockThreadDetail)

    const { result } = renderHook(
      () => useThreadDetail('T123456', 'C123456', '1234567890.123456'),
      {
        wrapper: createWrapper(),
      }
    )

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(mockThreadDetail)
  })

  it('should pass botId parameter when provided', async () => {
    vi.mocked(api.fetchThreadDetail).mockResolvedValue(mockThreadDetail)

    const { result } = renderHook(
      () => useThreadDetail('T123456', 'C123456', '1234567890.123456', 'T123456-test-channel'),
      {
        wrapper: createWrapper(),
      }
    )

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(api.fetchThreadDetail).toHaveBeenCalledWith(
      'T123456',
      'C123456',
      '1234567890.123456',
      'T123456-test-channel'
    )
  })

  it('should not fetch when parameters are undefined', () => {
    vi.mocked(api.fetchThreadDetail).mockResolvedValue(mockThreadDetail)

    const { result } = renderHook(
      () => useThreadDetail(undefined, 'C123456', '1234567890.123456'),
      {
        wrapper: createWrapper(),
      }
    )

    expect(result.current.isPending).toBe(true)
    expect(result.current.fetchStatus).toBe('idle')
    expect(api.fetchThreadDetail).not.toHaveBeenCalled()
  })

  it('should handle error state', async () => {
    const error = new Error('Network error')
    vi.mocked(api.fetchThreadDetail).mockRejectedValue(error)

    const { result } = renderHook(
      () => useThreadDetail('T123456', 'C123456', '1234567890.123456'),
      {
        wrapper: createWrapper(),
      }
    )

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(result.current.error).toBeTruthy()
  })

  it('should refetch when parameters change', async () => {
    vi.mocked(api.fetchThreadDetail).mockResolvedValue(mockThreadDetail)

    const { result, rerender } = renderHook(
      ({ teamId, channelId, threadTs }) => useThreadDetail(teamId, channelId, threadTs),
      {
        wrapper: createWrapper(),
        initialProps: {
          teamId: 'T123456',
          channelId: 'C123456',
          threadTs: '1234567890.123456',
        },
      }
    )

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(api.fetchThreadDetail).toHaveBeenCalledTimes(1)

    // Change parameters
    rerender({
      teamId: 'T789012',
      channelId: 'C789012',
      threadTs: '9876543210.654321',
    })

    await waitFor(() => expect(api.fetchThreadDetail).toHaveBeenCalledTimes(2))
    expect(api.fetchThreadDetail).toHaveBeenLastCalledWith(
      'T789012',
      'C789012',
      '9876543210.654321',
      undefined
    )
  })
})
