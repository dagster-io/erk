export interface AnalyticsEvent {
  id: number
  organization_id: number
  event_type: string
  event_timestamp: string
  metadata: Record<string, unknown> | string
  user_id: string | null
  channel_id: string | null
}

export interface AnalyticsResponse {
  events: AnalyticsEvent[]
  organization_id: number
  total: number
  page: number
  limit: number
}
