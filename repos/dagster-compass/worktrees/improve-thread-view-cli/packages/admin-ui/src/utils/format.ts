import { format, parseISO } from 'date-fns'

export function formatDate(dateString: string | null): string {
  if (!dateString) return '-'
  try {
    return format(parseISO(dateString), 'MMM d, yyyy h:mm a')
  } catch {
    return dateString
  }
}

export function formatShortDate(dateString: string | null): string {
  if (!dateString) return '-'
  try {
    return format(parseISO(dateString), 'MMM d, yyyy')
  } catch {
    return dateString
  }
}

export function copyToClipboard(text: string): Promise<void> {
  return navigator.clipboard.writeText(text)
}

export function getStripeUrl(isTestMode: boolean): string {
  return isTestMode ? 'https://dashboard.stripe.com/test' : 'https://dashboard.stripe.com'
}
