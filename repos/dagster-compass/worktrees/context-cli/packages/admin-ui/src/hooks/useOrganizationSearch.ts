import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { searchOrganizations } from '../api/organizations'

export function useOrganizationSearch(searchQuery: string, enabled: boolean = true) {
  const [debouncedQuery, setDebouncedQuery] = useState(searchQuery)

  // Debounce search query (300ms delay)
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery)
    }, 300)

    return () => clearTimeout(timer)
  }, [searchQuery])

  return useQuery({
    queryKey: ['organizations', 'search', debouncedQuery],
    queryFn: () => searchOrganizations(debouncedQuery, 50),
    enabled: enabled && debouncedQuery.length >= 2,
    staleTime: 1000 * 60, // Cache for 1 minute
  })
}
