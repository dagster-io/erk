import type { InviteToken } from '../types/token'
import { CopyButton } from './CopyButton'
import { formatDate } from '../utils/format'

interface TokenTableProps {
  tokens: InviteToken[]
}

export function TokenTable({ tokens }: TokenTableProps) {
  const getOnboardingLink = (token: string) => {
    const baseUrl = window.location.origin
    return `${baseUrl}/signup?referral-token=${token}`
  }

  return (
    <div className="table-container">
      <table className="data-table">
        <thead>
          <tr>
            <th>Token</th>
            <th>Type</th>
            <th>Bonus Answers</th>
            <th>Status</th>
            <th>Created</th>
            <th>Consumed</th>
            <th>Organizations</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {tokens.map((token) => {
            const isConsumed = token.consumed_at !== null
            const onboardingLink = getOnboardingLink(token.token)

            return (
              <tr key={token.id}>
                <td className="font-mono text-xs">
                  <div className="flex items-center space-x-2">
                    <span className="truncate max-w-[200px]">{token.token}</span>
                    <CopyButton text={token.token} label="Copy" />
                  </div>
                </td>
                <td>
                  <span
                    className={
                      token.is_single_use
                        ? 'badge bg-yellow-100 text-yellow-800'
                        : 'badge bg-green-100 text-green-800'
                    }
                  >
                    {token.is_single_use ? 'Single-use' : 'Multi-use'}
                  </span>
                </td>
                <td>{token.consumer_bonus_answers}</td>
                <td>
                  <span
                    className={
                      isConsumed
                        ? 'badge bg-gray-100 text-gray-800'
                        : 'badge bg-green-100 text-green-800'
                    }
                  >
                    {isConsumed ? 'Consumed' : 'Available'}
                  </span>
                </td>
                <td className="text-sm text-gray-600">{formatDate(token.created_at)}</td>
                <td className="text-sm text-gray-600">{formatDate(token.consumed_at)}</td>
                <td>
                  {token.consumed_by_organization_ids.length > 0 ? (
                    <div className="text-sm">
                      {token.consumed_by_organization_ids.map((orgId) => (
                        <div key={orgId}>
                          Org {orgId}
                          {token.organization_name && ` (${token.organization_name})`}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <span className="text-gray-400">-</span>
                  )}
                </td>
                <td>
                  <CopyButton
                    text={onboardingLink}
                    label="Copy Link"
                    className="text-blue-600 hover:text-blue-800"
                  />
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
