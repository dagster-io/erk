import { useState } from 'react'
import { useOrganizations, usePlanTypes, useConvertPlan } from '../hooks/useOrganizations'
import { useOrganizationSearch } from '../hooks/useOrganizationSearch'
import { SearchInput } from '../components/SearchInput'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { ErrorMessage } from '../components/ErrorMessage'
import { Pagination } from '../components/Pagination'
import { OrganizationTable } from '../components/OrganizationTable'

export function OrganizationsPage() {
  // Pagination state
  const [page, setPage] = useState(1)
  const [limit, setLimit] = useState(25)

  // Search state
  const [searchQuery, setSearchQuery] = useState('')
  const isSearchMode = searchQuery.length >= 2

  // Fetch data based on mode
  const paginatedQuery = useOrganizations(page, limit)
  const searchQueryResult = useOrganizationSearch(searchQuery, isSearchMode)

  // Use search results when searching, otherwise use paginated results
  const { data, isLoading, error } = isSearchMode ? searchQueryResult : paginatedQuery

  const convertPlan = useConvertPlan()

  // Fetch plan types for all organizations once they're loaded
  const orgIds = data?.organizations.map((org) => org.id) || []
  const { data: planTypesData } = usePlanTypes(orgIds)

  // Merge plan types into organizations
  const organizations = data?.organizations.map((org) => {
    const planInfo = planTypesData?.find((p) => p.organization_id === org.id)
    return {
      ...org,
      plan_type: planInfo?.plan_type || 'Unknown',
      plan_limit: planInfo?.plan_limits?.base_num_answers,
      allow_overage: planInfo?.plan_limits?.allow_overage,
    }
  })

  const handleConvertPlan = async (orgId: number, planType: string) => {
    if (!confirm(`Convert organization ${orgId} to ${planType} plan?`)) {
      return
    }

    try {
      await convertPlan.mutateAsync({
        orgId,
        planType: planType as any,
      })
      alert('Plan converted successfully!')
    } catch (error) {
      alert(`Failed to convert plan: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  const handleClearSearch = () => {
    setSearchQuery('')
    setPage(1)
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Organizations</h1>
        <p className="mt-2 text-sm text-gray-600">
          Manage organizations, view usage, and convert subscription plans
        </p>
      </div>

      {/* Search bar - always visible to prevent losing focus */}
      <div className="mb-6">
        <SearchInput
          value={searchQuery}
          onChange={setSearchQuery}
          onClear={handleClearSearch}
          placeholder="Search organizations by name..."
          isSearching={searchQueryResult.isFetching}
        />

        {/* Search results info */}
        {isSearchMode && data && 'total_matches' in data && (
          <div className="mt-2 text-sm text-gray-600">
            Found {data.total_matches} organization{data.total_matches !== 1 ? 's' : ''} matching "
            {searchQuery}"
            {data.total_matches > organizations!.length && (
              <span className="text-gray-500"> (showing first {organizations!.length})</span>
            )}
          </div>
        )}
      </div>

      {/* Error state */}
      {error && <ErrorMessage error={error} message="Failed to load organizations" />}

      {/* Loading state - show spinner but keep search input visible */}
      {isLoading ? (
        <LoadingSpinner />
      ) : organizations && organizations.length > 0 ? (
        <>
          <OrganizationTable organizations={organizations} onConvertPlan={handleConvertPlan} />

          {/* Only show pagination in browse mode, not search mode */}
          {!isSearchMode && 'total' in data! && (
            <Pagination
              page={page}
              limit={limit}
              total={data.total}
              onPageChange={setPage}
              onLimitChange={(newLimit) => {
                setLimit(newLimit)
                setPage(1)
              }}
            />
          )}
        </>
      ) : (
        <div className="text-center py-12 bg-white rounded-lg shadow">
          <p className="text-gray-500">
            {isSearchMode
              ? `No organizations found matching "${searchQuery}"`
              : 'No organizations found'}
          </p>
        </div>
      )}
    </div>
  )
}
