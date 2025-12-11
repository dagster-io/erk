import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '../test/test-utils'
import userEvent from '@testing-library/user-event'
import { ActionsDropdown } from './ActionsDropdown'

describe('ActionsDropdown', () => {
  const mockActions = [
    { label: 'Action 1', onClick: vi.fn() },
    { label: 'Action 2', onClick: vi.fn() },
    { label: 'Delete', onClick: vi.fn(), variant: 'danger' as const },
  ]

  it('should render dropdown button', () => {
    render(<ActionsDropdown actions={mockActions} />)
    expect(screen.getByRole('button', { name: /Actions/ })).toBeInTheDocument()
  })

  it('should show menu when clicking button', async () => {
    const user = userEvent.setup()
    render(<ActionsDropdown actions={mockActions} />)

    await user.click(screen.getByRole('button', { name: /Actions/ }))

    expect(screen.getByText('Action 1')).toBeInTheDocument()
    expect(screen.getByText('Action 2')).toBeInTheDocument()
    expect(screen.getByText('Delete')).toBeInTheDocument()
  })

  it('should call action onClick when clicking menu item', async () => {
    const user = userEvent.setup()
    render(<ActionsDropdown actions={mockActions} />)

    await user.click(screen.getByRole('button', { name: /Actions/ }))
    await user.click(screen.getByText('Action 1'))

    expect(mockActions[0].onClick).toHaveBeenCalled()
  })

  it('should close menu after clicking action', async () => {
    const user = userEvent.setup()
    render(<ActionsDropdown actions={mockActions} />)

    await user.click(screen.getByRole('button', { name: /Actions/ }))
    expect(screen.getByText('Action 1')).toBeInTheDocument()

    await user.click(screen.getByText('Action 1'))
    expect(screen.queryByText('Action 1')).not.toBeInTheDocument()
  })

  it('should close menu when clicking outside', async () => {
    const user = userEvent.setup()
    render(
      <div>
        <ActionsDropdown actions={mockActions} />
        <div data-testid="outside">Outside</div>
      </div>
    )

    await user.click(screen.getByRole('button', { name: /Actions/ }))
    expect(screen.getByText('Action 1')).toBeInTheDocument()

    await user.click(screen.getByTestId('outside'))
    expect(screen.queryByText('Action 1')).not.toBeInTheDocument()
  })

  it('should apply danger styling to danger variant actions', async () => {
    const user = userEvent.setup()
    render(<ActionsDropdown actions={mockActions} />)

    await user.click(screen.getByRole('button', { name: /Actions/ }))

    const deleteButton = screen.getByText('Delete')
    expect(deleteButton).toHaveClass('text-red-600')
  })
})
