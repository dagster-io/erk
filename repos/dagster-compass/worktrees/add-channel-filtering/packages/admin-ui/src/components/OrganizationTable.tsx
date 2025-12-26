import { Link } from 'react-router-dom'
import type { Organization } from '../types/organization'
import { PlanBadge } from './PlanBadge'
import { ActionsDropdown } from './ActionsDropdown'
import { getStripeUrl } from '../utils/format'

interface OrganizationTableProps {
  organizations: Organization[]
  onConvertPlan: (orgId: number, planType: string) => void
}

export function OrganizationTable({ organizations, onConvertPlan }: OrganizationTableProps) {
  // Detect Stripe test mode from first org with subscription
  const isTestMode = organizations.some(
    (org) =>
      org.stripe_subscription_id &&
      (org.stripe_subscription_id.includes('test') || org.stripe_customer_id?.includes('test'))
  )
  const stripeBaseUrl = getStripeUrl(isTestMode)

  return (
    <div className="bg-white rounded-lg shadow overflow-visible">
      <div className="overflow-x-auto">
        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Organization Name</th>
              <th>Plan Type</th>
              <th>Stripe Customer</th>
              <th>Stripe Subscription</th>
              <th>Bots</th>
              <th>Usage / Limit</th>
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
