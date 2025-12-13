import { describe, it, expect } from 'vitest'
import { render, screen } from '../test/test-utils'
import { PlanBadge } from './PlanBadge'

describe('PlanBadge', () => {
  it('should render Free plan badge', () => {
    render(<PlanBadge planType="Free" />)
    expect(screen.getByText('Free')).toBeInTheDocument()
    expect(screen.getByText('Free')).toHaveClass('badge-free')
  })

  it('should render Starter plan badge', () => {
    render(<PlanBadge planType="Starter" />)
    expect(screen.getByText('Starter')).toBeInTheDocument()
    expect(screen.getByText('Starter')).toHaveClass('badge-starter')
  })

  it('should render Team plan badge', () => {
    render(<PlanBadge planType="Team" />)
    expect(screen.getByText('Team')).toBeInTheDocument()
    expect(screen.getByText('Team')).toHaveClass('badge-team')
  })

  it('should render Design Partner plan badge', () => {
    render(<PlanBadge planType="Design Partner" />)
    expect(screen.getByText('Design Partner')).toBeInTheDocument()
    expect(screen.getByText('Design Partner')).toHaveClass('badge-design-partner')
  })

  it('should render Unknown plan badge', () => {
    render(<PlanBadge planType="Unknown" />)
    expect(screen.getByText('Unknown')).toBeInTheDocument()
    expect(screen.getByText('Unknown')).toHaveClass('badge-unknown')
  })
})
