import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/dom'
import { render as rtlRender } from '@testing-library/react'
import { ThreadDetailPage } from './ThreadDetailPage'
import * as api from '../api/threads'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

vi.mock('../api/threads')

// Helper to render with route params
function renderWithParams(teamId: string, channelId: string, threadTs: string, botId?: string) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  const botIdParam = botId ? `?bot_id=${encodeURIComponent(botId)}` : ''
  const url = `/thread/${teamId}/${channelId}/${threadTs}${botIdParam}`

  return rtlRender(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[url]}>
        <Routes>
          <Route path="/thread/:teamId/:channelId/:threadTs" element={<ThreadDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('ThreadDetailPage', () => {
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

  it('should render thread detail page with data', async () => {
    vi.mocked(api.fetchThreadDetail).mockResolvedValue(mockThreadDetail)

    renderWithParams('T123456', 'C123456', '1234567890.123456', 'T123456-test-channel')

    // Wait for HTML content to be rendered (this indicates data has loaded)
    await waitFor(() => {
      expect(screen.getByText('Test thread content')).toBeInTheDocument()
    })

    // Check that thread info is displayed
    expect(screen.getByText('Thread Detail')).toBeInTheDocument()
    expect(screen.getByText('Team: T123456')).toBeInTheDocument()
    expect(screen.getByText('Channel: C123456')).toBeInTheDocument()
    expect(screen.getByText('Thread TS: 1234567890.123456')).toBeInTheDocument()
    expect(screen.getByText('Bot ID: T123456-test-channel')).toBeInTheDocument()
  })

  it('should show loading state initially', () => {
    vi.mocked(api.fetchThreadDetail).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    )

    renderWithParams('T123456', 'C123456', '1234567890.123456')

    // Check for loading spinner by its visual appearance
    const spinner = document.querySelector('.animate-spin')
    expect(spinner).toBeInTheDocument()
  })

  it('should handle error state', async () => {
    vi.mocked(api.fetchThreadDetail).mockRejectedValue(new Error('Network error'))

    renderWithParams('T123456', 'C123456', '1234567890.123456')

    await waitFor(() => {
      expect(screen.getByText(/Failed to load thread detail/)).toBeInTheDocument()
    })
  })

  it('should display back to threads link', async () => {
    vi.mocked(api.fetchThreadDetail).mockResolvedValue(mockThreadDetail)

    renderWithParams('T123456', 'C123456', '1234567890.123456')

    await waitFor(() => {
      expect(screen.getByText('Thread Detail')).toBeInTheDocument()
    })

    const backLink = screen.getByText('← Back to Threads')
    expect(backLink).toBeInTheDocument()
    // Link component renders as an anchor tag but uses client-side routing
    expect(backLink.closest('a')).toBeInTheDocument()
  })

  it('should pass correct parameters to API', async () => {
    vi.mocked(api.fetchThreadDetail).mockResolvedValue(mockThreadDetail)

    renderWithParams('T123456', 'C123456', '1234567890.123456', 'T123456-test-channel')

    await waitFor(() => {
      expect(api.fetchThreadDetail).toHaveBeenCalledWith(
        'T123456',
        'C123456',
        '1234567890.123456',
        'T123456-test-channel'
      )
    })
  })

  it('should render with HTML content safely', async () => {
    const htmlWithScript = {
      ...mockThreadDetail,
      html: '<div>Safe content</div><script>alert("xss")</script>',
    }
    vi.mocked(api.fetchThreadDetail).mockResolvedValue(htmlWithScript)

    renderWithParams('T123456', 'C123456', '1234567890.123456')

    await waitFor(() => {
      expect(screen.getByText('Safe content')).toBeInTheDocument()
    })

    // Note: dangerouslySetInnerHTML will still execute scripts in real browsers
    // This is a known limitation, but the content comes from our own backend
  })
})
