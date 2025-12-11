import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '../test/test-utils'
import userEvent from '@testing-library/user-event'
import { CopyButton } from './CopyButton'

describe('CopyButton', () => {
  beforeEach(() => {
    // Mock clipboard API properly
    Object.defineProperty(navigator, 'clipboard', {
      value: {
        writeText: vi.fn(() => Promise.resolve()),
      },
      writable: true,
      configurable: true,
    })
  })

  it('should render copy button with default label', () => {
    render(<CopyButton text="test text" />)
    expect(screen.getByRole('button', { name: /Copy/ })).toBeInTheDocument()
  })

  it('should render copy button with custom label', () => {
    render(<CopyButton text="test text" label="Copy Link" />)
    expect(screen.getByRole('button', { name: /Copy Link/ })).toBeInTheDocument()
  })

  it('should copy text to clipboard when clicked', async () => {
    const user = userEvent.setup()
    const writeTextMock = vi.fn(() => Promise.resolve())

    Object.defineProperty(navigator, 'clipboard', {
      value: {
        writeText: writeTextMock,
      },
      writable: true,
      configurable: true,
    })

    render(<CopyButton text="test text" />)

    await user.click(screen.getByRole('button'))
    expect(writeTextMock).toHaveBeenCalledWith('test text')
  })

  it('should show "Copied!" message after successful copy', async () => {
    const user = userEvent.setup()
    render(<CopyButton text="test text" />)

    await user.click(screen.getByRole('button'))

    await waitFor(() => {
      expect(screen.getByText('✓ Copied!')).toBeInTheDocument()
    })
  })
})
