import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/dom'
import userEvent from '@testing-library/user-event'
import { render } from '../test/test-utils'
import { TokensPage } from './TokensPage'
import * as api from '../api/tokens'

vi.mock('../api/tokens')

describe('TokensPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    vi.mocked(api.fetchTokens).mockResolvedValue({
      tokens: [
        {
          id: 1,
          token: 'test-token-123',
          created_at: '2024-01-01T00:00:00Z',
          consumed_at: null,
          is_single_use: false,
          consumer_bonus_answers: 150,
          consumed_by_organization_ids: [],
          organization_name: null,
          organization_id: null,
        },
      ],
    })
  })

  it('should render tokens page', async () => {
    render(<TokensPage />)

    // Wait for data to load first
    await waitFor(() => {
      expect(screen.getByText('test-token-123')).toBeInTheDocument()
    })

    expect(screen.getByText('Invite Tokens')).toBeInTheDocument()
    expect(screen.getByText(/Create and manage invitation tokens/)).toBeInTheDocument()
  })

  it('should show create token button', async () => {
    render(<TokensPage />)

    // Wait for page to load
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Create Token/ })).toBeInTheDocument()
    })
  })

  it('should toggle token form when clicking create button', async () => {
    const user = userEvent.setup()
    render(<TokensPage />)

    // Wait for page to load
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Create Token/ })).toBeInTheDocument()
    })

    const createButton = screen.getByRole('button', { name: /Create Token/ })
    await user.click(createButton)

    expect(screen.getByText('Create New Token')).toBeInTheDocument()

    // Click again to hide
    await user.click(screen.getByRole('button', { name: /Cancel/ }))
    expect(screen.queryByText('Create New Token')).not.toBeInTheDocument()
  })

  it('should display token data in table', async () => {
    render(<TokensPage />)

    await waitFor(() => {
      expect(screen.getByText('test-token-123')).toBeInTheDocument()
      expect(screen.getByText('150')).toBeInTheDocument()
      expect(screen.getByText('Available')).toBeInTheDocument()
    })
  })

  it('should handle empty state', async () => {
    vi.mocked(api.fetchTokens).mockResolvedValue({ tokens: [] })

    render(<TokensPage />)

    await waitFor(() => {
      expect(screen.getByText('No tokens found')).toBeInTheDocument()
    })
  })

  it('should handle error state', async () => {
    vi.mocked(api.fetchTokens).mockRejectedValue(new Error('Failed to fetch'))

    render(<TokensPage />)

    await waitFor(() => {
      expect(screen.getByText(/Failed to load tokens/)).toBeInTheDocument()
    })
  })
})
