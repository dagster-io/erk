export interface Organization {
  id: number
  name: string
  industry: string | null
  stripe_customer_id: string | null
  stripe_subscription_id: string | null
  bot_count: number
  current_usage: number
  bonus_answers: number
  plan_type?: PlanType
  plan_limit?: number
  allow_overage?: boolean
}

export type PlanType = 'Free' | 'Starter' | 'Team' | 'Design Partner' | 'Unknown'

export interface PlanLimits {
  base_num_answers: number
  allow_overage: boolean
  num_channels: number
  allow_additional_channels: boolean
}

export interface OrganizationPlanInfo {
  organization_id: number
  plan_type: PlanType
  plan_limits: PlanLimits | null
}

export interface OrganizationsResponse {
  organizations: Organization[]
  total: number
  page: number
  limit: number
}

export interface SearchOrganizationsResponse {
  organizations: Organization[]
  total_matches: number
  query: string
}
