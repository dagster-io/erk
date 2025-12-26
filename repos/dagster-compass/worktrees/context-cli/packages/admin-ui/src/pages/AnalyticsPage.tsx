import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useAnalytics } from '../hooks/useAnalytics'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { ErrorMessage } from '../components/ErrorMessage'
import { Pagination } from '../components/Pagination'
import { AnalyticsEventTable } from '../components/AnalyticsEventTable'

export function AnalyticsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [orgId, setOrgId] = useState<number | null>(null)
  const [page, setPage] = useState(1)
  const [limit, setLimit] = useState(50)

  // Get organization_id from URL query params
  useEffect(() => {
    const orgIdParam = searchParams.get('organization_id')
    if (orgIdParam) {
      setOrgId(Number(orgIdParam))
    }
  }, [searchParams])

  const { data, isLoading, error } = useAnalytics(orgId, page, limit)

  const handleOrgIdChange = (newOrgId: string) => {
    const id = Number(newOrgId)
    if (id > 0) {
      setOrgId(id)
      setSearchParams({ organization_id: newOrgId })
      setPage(1)
    }
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Analytics Events</h1>
        <p className="mt-2 text-sm text-gray-600">
          View detailed analytics events for organizations
        </p>
      </div>

      <div className="mb-6 card">
        <label className="form-label">Organization ID</label>
        <input
          type="number"
          value={orgId || ''}
          onChange={(e) => handleOrgIdChange(e.target.value)}
          placeholder="Enter organization ID"
          className="form-input max-w-md"
          min={1}
        />
      </div>

      {!orgId ? (
        <div className="text-center py-12 bg-white rounded-lg shadow">
          <p className="text-gray-500">Enter an organization ID to view analytics events</p>
        </div>
      ) : isLoading ? (
        <LoadingSpinner />
      ) : error ? (
        <ErrorMessage error={error} message="Failed to load analytics events" />
      ) : data?.events && data.events.length > 0 ? (
        <>
          <AnalyticsEventTable events={data.events} />
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
        </>
      ) : (
        <div className="text-center py-12 bg-white rounded-lg shadow">
          <p className="text-gray-500">No analytics events found for this organization</p>
        </div>
      )}
    </div>
  )
}
