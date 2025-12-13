import { Link } from 'react-router-dom'
import type { Organization } from '../types/organization'
import { PlanBadge } from './PlanBadge'

interface OrganizationTableProps {
  organizations: Organization[]
  sortBy?: string
  order?: 'asc' | 'desc'
  onSortChange?: (field: string) => void
}

export function OrganizationTable({
  organizations,
  sortBy,
  order,
  onSortChange,
}: OrganizationTableProps) {
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
        <table className="data-table w-full">
          <thead>
            <tr>
              <SortableHeader field="id">ID</SortableHeader>
              <SortableHeader field="name">Organization Name</SortableHeader>
              <th>Plan Type</th>
              <SortableHeader field="bot_count">Bots</SortableHeader>
              <SortableHeader field="usage">Usage / Limit</SortableHeader>
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
                  <td className="font-medium">
                    <Link
                      to={`/organizations/${org.id}`}
                      className="text-blue-600 hover:text-blue-800 hover:underline"
                    >
                      {org.name}
                    </Link>
                  </td>
                  <td>
                    {org.plan_type ? (
                      <PlanBadge planType={org.plan_type} />
                    ) : (
                      <span className="text-gray-400 text-sm">Loading...</span>
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
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
