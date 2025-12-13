import { describe, it, expect } from 'vitest'
import { render, screen } from '../test/test-utils'
import { LoadingSpinner, LoadingText } from './LoadingSpinner'

describe('LoadingSpinner', () => {
  it('should render spinner', () => {
    const { container } = render(<LoadingSpinner />)
    expect(container.querySelector('.animate-spin')).toBeInTheDocument()
  })
})

describe('LoadingText', () => {
  it('should render default loading text', () => {
    render(<LoadingText />)
    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('should render custom loading text', () => {
    render(<LoadingText text="Please wait..." />)
    expect(screen.getByText('Please wait...')).toBeInTheDocument()
  })
})
