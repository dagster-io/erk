import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '../test/test-utils'
import userEvent from '@testing-library/user-event'
import { SearchInput } from './SearchInput'

describe('SearchInput', () => {
  it('should render search input', () => {
    render(<SearchInput value="" onChange={vi.fn()} onClear={vi.fn()} />)

    expect(screen.getByPlaceholderText('Search organizations...')).toBeInTheDocument()
  })

  it('should render with custom placeholder', () => {
    render(
      <SearchInput value="" onChange={vi.fn()} onClear={vi.fn()} placeholder="Custom placeholder" />
    )

    expect(screen.getByPlaceholderText('Custom placeholder')).toBeInTheDocument()
  })

  it('should call onChange when typing', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()

    render(<SearchInput value="" onChange={onChange} onClear={vi.fn()} />)

    const input = screen.getByRole('textbox')
    await user.type(input, 'test')

    expect(onChange).toHaveBeenCalledTimes(4)
    expect(onChange).toHaveBeenLastCalledWith('test')
  })

  it('should show clear button when has value', () => {
    render(<SearchInput value="test" onChange={vi.fn()} onClear={vi.fn()} />)

    expect(screen.getByLabelText('Clear search')).toBeInTheDocument()
  })

  it('should not show clear button when empty', () => {
    render(<SearchInput value="" onChange={vi.fn()} onClear={vi.fn()} />)

    expect(screen.queryByLabelText('Clear search')).not.toBeInTheDocument()
  })

  it('should call onClear when clicking clear button', async () => {
    const user = userEvent.setup()
    const onClear = vi.fn()

    render(<SearchInput value="test" onChange={vi.fn()} onClear={onClear} />)

    await user.click(screen.getByLabelText('Clear search'))
    expect(onClear).toHaveBeenCalled()
  })

  it('should show loading spinner when isSearching', () => {
    const { container } = render(
      <SearchInput value="test" onChange={vi.fn()} onClear={vi.fn()} isSearching={true} />
    )

    expect(container.querySelector('.animate-spin')).toBeInTheDocument()
  })

  it('should show helper text when value length < 2', () => {
    render(<SearchInput value="a" onChange={vi.fn()} onClear={vi.fn()} />)

    expect(screen.getByText('Type at least 2 characters to search')).toBeInTheDocument()
  })

  it('should not show helper text when value length >= 2', () => {
    render(<SearchInput value="ab" onChange={vi.fn()} onClear={vi.fn()} />)

    expect(screen.queryByText('Type at least 2 characters to search')).not.toBeInTheDocument()
  })
})
