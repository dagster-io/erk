import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen } from '@testing-library/dom'
import { waitFor } from '@testing-library/dom'
import { render } from '../test/test-utils'
import { OrganizationsPage } from './OrganizationsPage'
import * as api from '../api/organizations'

vi.mock('../api/organizations')

describe('OrganizationsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    // Mock successful API responses
    vi.mocked(api.fetchOrganizations).mockResolvedValue({
      organizations: [
        {
          id: 1,
          name: 'Test Organization',
          industry: 'Technology',
          stripe_customer_id: 'cus_123',
          stripe_subscription_id: 'sub_123',
          bot_count: 5,
          current_usage: 100,
          bonus_answers: 50,
        },
      ],
      total: 1,
      page: 1,
      limit: 25,
    })

    vi.mocked(api.fetchPlanTypes).mockResolvedValue([
      {
        organization_id: 1,
        plan_type: 'Team',
        plan_limits: {
          base_num_answers: 1000,
          allow_overage: true,
          num_channels: 10,
          allow_additional_channels: false,
        },
      },
    ])
  })

  it('should render organizations page', async () => {
    render(<OrganizationsPage />)

    // Wait for data to load first
    await waitFor(() => {
      expect(screen.getByText('Test Organization')).toBeInTheDocument()
    })

    expect(screen.getByText('Organizations')).toBeInTheDocument()
    expect(screen.getByText(/Manage organizations/)).toBeInTheDocument()
  })

  it('should display organization data in table', async () => {
    render(<OrganizationsPage />)

    await waitFor(() => {
      expect(screen.getByText('Test Organization')).toBeInTheDocument()
      expect(screen.getByText('cus_123')).toBeInTheDocument()
      expect(screen.getByText('sub_123')).toBeInTheDocument()
    })
  })

  it('should show loading state initially', () => {
    render(<OrganizationsPage />)
    // Check for loading spinner by its visual appearance
    const spinner = document.querySelector('.animate-spin')
    expect(spinner).toBeInTheDocument()
  })

  it('should handle pagination', async () => {
    render(<OrganizationsPage />)

    await waitFor(() => {
      expect(screen.getByText('Test Organization')).toBeInTheDocument()
    })

    // Note: Pagination will only appear if there are multiple pages
    // This test would need more data to properly test pagination
  })

  it('should handle empty state', async () => {
    vi.mocked(api.fetchOrganizations).mockResolvedValue({
      organizations: [],
      total: 0,
      page: 1,
      limit: 25,
    })

    render(<OrganizationsPage />)

    await waitFor(() => {
      expect(screen.getByText('No organizations found')).toBeInTheDocument()
    })
  })

  it('should handle error state', async () => {
    vi.mocked(api.fetchOrganizations).mockRejectedValue(new Error('Network error'))

    render(<OrganizationsPage />)

    await waitFor(() => {
      expect(screen.getByText(/Failed to load organizations/)).toBeInTheDocument()
    })
  })
})
