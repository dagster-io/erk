import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '../test/test-utils'
import userEvent from '@testing-library/user-event'
import { Pagination } from './Pagination'

describe('Pagination', () => {
  it('should render pagination controls', () => {
    const onPageChange = vi.fn()
    const onLimitChange = vi.fn()

    render(
      <Pagination
        page={1}
        limit={25}
        total={100}
        onPageChange={onPageChange}
        onLimitChange={onLimitChange}
      />
    )

    expect(screen.getByText(/Page 1/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Previous/ })).toBeDisabled()
    expect(screen.getByRole('button', { name: /Next/ })).not.toBeDisabled()
  })

  it('should call onPageChange when clicking next', async () => {
    const user = userEvent.setup()
    const onPageChange = vi.fn()
    const onLimitChange = vi.fn()

    render(
      <Pagination
        page={1}
        limit={25}
        total={100}
        onPageChange={onPageChange}
        onLimitChange={onLimitChange}
      />
    )

    await user.click(screen.getByRole('button', { name: /Next/ }))
    expect(onPageChange).toHaveBeenCalledWith(2)
  })

  it('should call onPageChange when clicking previous', async () => {
    const user = userEvent.setup()
    const onPageChange = vi.fn()
    const onLimitChange = vi.fn()

    render(
      <Pagination
        page={2}
        limit={25}
        total={100}
        onPageChange={onPageChange}
        onLimitChange={onLimitChange}
      />
    )

    await user.click(screen.getByRole('button', { name: /Previous/ }))
    expect(onPageChange).toHaveBeenCalledWith(1)
  })

  it('should call onLimitChange when changing page size', async () => {
    const user = userEvent.setup()
    const onPageChange = vi.fn()
    const onLimitChange = vi.fn()

    render(
      <Pagination
        page={1}
        limit={25}
        total={100}
        onPageChange={onPageChange}
        onLimitChange={onLimitChange}
      />
    )

    const select = screen.getByRole('combobox')
    await user.selectOptions(select, '50')
    expect(onLimitChange).toHaveBeenCalledWith(50)
  })

  it('should disable next button on last page', () => {
    const onPageChange = vi.fn()
    const onLimitChange = vi.fn()

    render(
      <Pagination
        page={4}
        limit={25}
        total={100}
        onPageChange={onPageChange}
        onLimitChange={onLimitChange}
      />
    )

    expect(screen.getByRole('button', { name: /Next/ })).toBeDisabled()
  })
})
