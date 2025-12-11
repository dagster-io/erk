import { useQuery } from '@tanstack/react-query'
import { fetchAnalytics } from '../api/analytics'

export function useAnalytics(organizationId: number | null, page: number, limit: number) {
  return useQuery({
    queryKey: ['analytics', organizationId, page, limit],
    queryFn: () => fetchAnalytics(organizationId!, page, limit),
    enabled: organizationId !== null,
  })
}
