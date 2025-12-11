import { describe, it, expect, vi, beforeEach } from 'vitest'
import { formatDate, formatShortDate, copyToClipboard, getStripeUrl } from './format'

describe('formatDate', () => {
  it('should format valid date string', () => {
    const result = formatDate('2024-01-15T10:30:00Z')
    expect(result).toMatch(/Jan 15, 2024/)
  })

  it('should return "-" for null', () => {
    expect(formatDate(null)).toBe('-')
  })

  it('should return original string for invalid date', () => {
    const invalid = 'not-a-date'
    expect(formatDate(invalid)).toBe(invalid)
  })
})

describe('formatShortDate', () => {
  it('should format valid date string without time', () => {
    const result = formatShortDate('2024-01-15T10:30:00Z')
    expect(result).toMatch(/Jan 15, 2024/)
    expect(result).not.toMatch(/10:30/)
  })

  it('should return "-" for null', () => {
    expect(formatShortDate(null)).toBe('-')
  })

  it('should return original string for invalid date', () => {
    const invalid = 'invalid-date'
    expect(formatShortDate(invalid)).toBe(invalid)
  })
})

describe('copyToClipboard', () => {
  beforeEach(() => {
    // Mock clipboard API
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn(() => Promise.resolve()),
      },
    })
  })

  it('should copy text to clipboard', async () => {
    await copyToClipboard('test text')
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('test text')
  })
})

describe('getStripeUrl', () => {
  it('should return test URL when isTestMode is true', () => {
    expect(getStripeUrl(true)).toBe('https://dashboard.stripe.com/test')
  })

  it('should return production URL when isTestMode is false', () => {
    expect(getStripeUrl(false)).toBe('https://dashboard.stripe.com')
  })
})
