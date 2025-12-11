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

interface TemporalConfig {
  type: 'cloud' | 'oss'
  namespace: string
}

/**
 * Get the Temporal workflows URL for an organization.
 * Uses actual Temporal config from backend to build appropriate URL.
 *
 * - Cloud: Uses search attribute filter: `organization`="OrgName"
 * - OSS: Links to main workflows page (OSS doesn't have organization search attributes configured)
 */
export function getTemporalWorkflowsUrl(
  organizationName: string,
  temporalConfig?: TemporalConfig
): string {
  if (!temporalConfig) {
    // Fallback to local if config not loaded yet
    return `http://localhost:8233/namespaces/default/workflows`
  }

  if (temporalConfig.type === 'cloud') {
    // Temporal Cloud: Use search attribute filter
    const query = encodeURIComponent(`\`organization\`="${organizationName}"`)
    return `https://cloud.temporal.io/namespaces/${temporalConfig.namespace}/workflows?query=${query}`
  } else {
    // Temporal OSS: Just link to main workflows page
    // OSS doesn't have custom search attributes configured, and workflow IDs don't contain org names
    return `http://localhost:8233/namespaces/${temporalConfig.namespace}/workflows`
  }
}
