export interface InviteToken {
  id: number
  token: string
  created_at: string
  consumed_at: string | null
  is_single_use: boolean
  consumer_bonus_answers: number
  consumed_by_organization_ids: number[]
  organization_name: string | null
  organization_id: number | null
}

export interface CreateTokenRequest {
  token?: string
  is_single_use: boolean
  consumer_bonus_answers: number
}

export interface CreateTokenResponse {
  success: boolean
  token?: string
  error?: string
}

export interface TokensResponse {
  tokens: InviteToken[]
}
