import { useQuery } from '@tanstack/react-query'
import { fetchThreadDetail } from '../api/threads'

export function useThreadDetail(
  teamId: string | undefined,
  channelId: string | undefined,
  threadTs: string | undefined,
  botId?: string
) {
  return useQuery({
    queryKey: ['threadDetail', teamId, channelId, threadTs, botId],
    queryFn: () => fetchThreadDetail(teamId!, channelId!, threadTs!, botId),
    enabled: Boolean(teamId && channelId && threadTs),
  })
}
