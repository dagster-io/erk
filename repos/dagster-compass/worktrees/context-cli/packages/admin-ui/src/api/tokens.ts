import { apiRequest } from './client'
import type {
  TokensResponse,
  CreateTokenRequest,
  CreateTokenResponse,
} from '../types/token'

export async function fetchTokens(): Promise<TokensResponse> {
  return apiRequest<TokensResponse>('/api/tokens')
}

export async function createToken(data: CreateTokenRequest): Promise<CreateTokenResponse> {
  return apiRequest<CreateTokenResponse>('/api/tokens', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}
