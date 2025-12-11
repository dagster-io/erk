import { useQuery } from '@tanstack/react-query'
import { fetchThreads } from '../api/threads'

export function useThreads(
  organizationId: number | null,
  page: number,
  limit: number,
  channelId?: string
) {
  return useQuery({
    queryKey: ['threads', organizationId, page, limit, channelId],
    queryFn: () => fetchThreads(organizationId!, page, limit, channelId),
    enabled: organizationId !== null,
  })
}
