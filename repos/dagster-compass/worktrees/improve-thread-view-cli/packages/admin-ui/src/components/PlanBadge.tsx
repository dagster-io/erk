import type { PlanType } from '../types/organization'
import clsx from 'clsx'

interface PlanBadgeProps {
  planType: PlanType
}

export function PlanBadge({ planType }: PlanBadgeProps) {
  const badgeClass = clsx('badge', {
    'badge-free': planType === 'Free',
    'badge-starter': planType === 'Starter',
    'badge-team': planType === 'Team',
    'badge-design-partner': planType === 'Design Partner',
    'badge-unknown': planType === 'Unknown',
  })

  return <span className={badgeClass}>{planType}</span>
}
