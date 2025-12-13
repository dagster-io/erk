import { useQuery } from '@tanstack/react-query'
import { fetchThreads } from '../api/threads'

export function useThreads(organizationId: number | null, page: number, limit: number) {
  return useQuery({
    queryKey: ['threads', organizationId, page, limit],
    queryFn: () => fetchThreads(organizationId!, page, limit),
    enabled: organizationId !== null,
  })
}
