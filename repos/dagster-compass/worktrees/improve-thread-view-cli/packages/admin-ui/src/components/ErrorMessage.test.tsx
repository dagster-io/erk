import { describe, it, expect } from 'vitest'
import { render, screen } from '../test/test-utils'
import { ErrorMessage } from './ErrorMessage'

describe('ErrorMessage', () => {
  it('should render nothing when no error and no message', () => {
    const { container } = render(<ErrorMessage error={null} />)
    expect(container.firstChild).toBeNull()
  })

  it('should render error message from Error object', () => {
    const error = new Error('Something went wrong')
    render(<ErrorMessage error={error} />)

    expect(screen.getByText('An error occurred')).toBeInTheDocument()
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
  })

  it('should render custom message', () => {
    render(<ErrorMessage error={null} message="Failed to load data" />)
    expect(screen.getByText('Failed to load data')).toBeInTheDocument()
  })

  it('should render custom message with error details', () => {
    const error = new Error('Network error')
    render(<ErrorMessage error={error} message="Failed to fetch" />)

    expect(screen.getByText('Failed to fetch')).toBeInTheDocument()
    expect(screen.getByText('Network error')).toBeInTheDocument()
  })
})
