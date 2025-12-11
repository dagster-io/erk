import { Link } from 'react-router-dom'
import type { Organization } from '../types/organization'
import { PlanBadge } from './PlanBadge'
import { ActionsDropdown } from './ActionsDropdown'
import { getStripeUrl, getTemporalWorkflowsUrl } from '../utils/format'
import { useConfig } from '../hooks/useConfig'

interface OrganizationTableProps {
  organizations: Organization[]
  onConvertPlan: (orgId: number, planType: string) => void
  sortBy?: string
  order?: 'asc' | 'desc'
  onSortChange?: (field: string) => void
}

export function OrganizationTable({
  organizations,
  onConvertPlan,
  sortBy,
  order,
  onSortChange,
}: OrganizationTableProps) {
  // Fetch config for Temporal URL building
  const { data: config } = useConfig() // Config is { temporal: { type, namespace } } or undefined

  // Detect Stripe test mode from first org with subscription
  const isTestMode = organizations.some(
    (org) =>
      org.stripe_subscription_id &&
      (org.stripe_subscription_id.includes('test') || org.stripe_customer_id?.includes('test'))
  )
  const stripeBaseUrl = getStripeUrl(isTestMode)

  // Helper to render sortable column header
  const SortableHeader = ({ field, children }: { field: string; children: React.ReactNode }) => {
    const isActive = sortBy === field
    const showArrow = isActive && onSortChange

    return (
      <th
        className={onSortChange ? 'cursor-pointer select-none hover:bg-gray-50' : ''}
        onClick={() => onSortChange?.(field)}
      >
        <div className="flex items-center gap-1">
          {children}
          {showArrow && <span className="text-xs">{order === 'asc' ? '↑' : '↓'}</span>}
        </div>
      </th>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-visible">
      <div className="overflow-x-auto">
        <table className="data-table">
          <thead>
            <tr>
              <SortableHeader field="id">ID</SortableHeader>
              <SortableHeader field="name">Organization Name</SortableHeader>
              <th>Plan Type</th>
              <th>Stripe Customer</th>
              <th>Stripe Subscription</th>
              <SortableHeader field="bot_count">Bots</SortableHeader>
              <SortableHeader field="usage">Usage / Limit</SortableHeader>
              <th>Threads</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {organizations.map((org) => {
              const isOverLimit =
                org.plan_limit !== undefined &&
                org.current_usage > org.plan_limit &&
                !org.allow_overage

              return (
                <tr key={org.id} className="relative">
                  <td className="font-mono text-xs">{org.id}</td>
                  <td className="font-medium">{org.name}</td>
                  <td>
                    {org.plan_type ? (
                      <PlanBadge planType={org.plan_type} />
                    ) : (
                      <span className="text-gray-400 text-sm">Loading...</span>
                    )}
                  </td>
                  <td>
                    {org.stripe_customer_id ? (
                      <a
                        href={`${stripeBaseUrl}/customers/${org.stripe_customer_id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:text-blue-800 text-sm font-mono"
                      >
                        {org.stripe_customer_id}
                      </a>
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
                  </td>
                  <td>
                    {org.stripe_subscription_id ? (
                      <a
                        href={`${stripeBaseUrl}/subscriptions/${org.stripe_subscription_id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:text-blue-800 text-sm font-mono"
                      >
                        {org.stripe_subscription_id}
                      </a>
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
                  </td>
                  <td>{org.bot_count}</td>
                  <td>
                    <span className={isOverLimit ? 'text-red-600 font-medium' : ''}>
                      {org.current_usage}
                      {org.bonus_answers > 0 && (
                        <span className="text-green-600"> (+{org.bonus_answers})</span>
                      )}
                      {org.plan_limit !== undefined ? (
                        <span className="text-gray-500"> / {org.plan_limit}</span>
                      ) : (
                        <span className="text-gray-400 text-sm"> / Loading...</span>
                      )}
                    </span>
                  </td>
                  <td>
                    <Link
                      to={`/threads?organization_id=${org.id}`}
                      className="text-blue-600 hover:text-blue-800 text-sm hover:underline"
                    >
                      View Threads
                    </Link>
                  </td>
                  <td className="relative">
                    <ActionsDropdown
                      actions={[
                        {
                          label: 'View Analytics',
                          onClick: () => {
                            window.location.href = `/analytics?organization_id=${org.id}`
                          },
                        },
                        {
                          label: 'View Temporal Workflows',
                          href: getTemporalWorkflowsUrl(org.name, config?.temporal),
                        },
                        {
                          label: 'Convert to Design Partner',
                          onClick: () => onConvertPlan(org.id, 'Design Partner'),
                        },
                        {
                          label: 'Convert to Team',
                          onClick: () => onConvertPlan(org.id, 'Team'),
                        },
                        {
                          label: 'Convert to Starter',
                          onClick: () => onConvertPlan(org.id, 'Starter'),
                        },
                        {
                          label: 'Convert to Free',
                          onClick: () => onConvertPlan(org.id, 'Free'),
                        },
                      ]}
                    />
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
