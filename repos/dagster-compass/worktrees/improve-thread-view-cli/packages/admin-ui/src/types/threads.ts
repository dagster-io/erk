export interface Thread {
  bot_id: string
  channel_id: string
  thread_ts: string
  event_count: number
  organization_id: number
  organization_name: string
}

export interface ThreadsResponse {
  threads: Thread[]
  organization_id: number
  total: number
  page: number
  limit: number
}

export interface ThreadDetail {
  bot_id: string
  team_id: string
  channel_id: string
  thread_ts: string
  html: string
}
