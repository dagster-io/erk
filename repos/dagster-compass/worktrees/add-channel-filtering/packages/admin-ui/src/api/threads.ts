import { apiRequest } from './client'
import type { ThreadsResponse, ThreadDetail } from '../types/threads'

export async function fetchThreads(
  organizationId: number,
  page: number = 1,
  limit: number = 50,
  channelId?: string
): Promise<ThreadsResponse> {
  const channelIdParam = channelId ? `&channel_id=${encodeURIComponent(channelId)}` : ''
  return apiRequest<ThreadsResponse>(
    `/api/threads?organization_id=${organizationId}&page=${page}&limit=${limit}${channelIdParam}`
  )
}

export async function fetchThreadDetail(
  teamId: string,
  channelId: string,
  threadTs: string,
  botId?: string
): Promise<ThreadDetail> {
  const botIdParam = botId ? `?bot_id=${encodeURIComponent(botId)}` : ''
  return apiRequest<ThreadDetail>(
    `/api/thread/${encodeURIComponent(teamId)}/${encodeURIComponent(channelId)}/${encodeURIComponent(threadTs)}${botIdParam}`
  )
}
