import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useThreads } from '../hooks/useThreads'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { ErrorMessage } from '../components/ErrorMessage'
import { Pagination } from '../components/Pagination'
import { ThreadsTable } from '../components/ThreadsTable'

export function ThreadsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [orgId, setOrgId] = useState<number | null>(null)
  const [channelId, setChannelId] = useState<string>('')
  const [page, setPage] = useState(1)
  const [limit, setLimit] = useState(50)

  // Get organization_id and channel_id from URL query params
  useEffect(() => {
    const orgIdParam = searchParams.get('organization_id')
    if (orgIdParam) {
      setOrgId(Number(orgIdParam))
    }
    const channelIdParam = searchParams.get('channel_id')
    if (channelIdParam) {
      setChannelId(channelIdParam)
    }
  }, [searchParams])

  const { data, isLoading, error } = useThreads(orgId, page, limit, channelId || undefined)

  const handleOrgIdChange = (newOrgId: string) => {
    const id = Number(newOrgId)
    if (id > 0) {
      setOrgId(id)
      const params: Record<string, string> = { organization_id: newOrgId }
      if (channelId) {
        params.channel_id = channelId
      }
      setSearchParams(params)
      setPage(1)
    }
  }

  const handleChannelIdChange = (newChannelId: string) => {
    setChannelId(newChannelId)
    if (orgId) {
      const params: Record<string, string> = { organization_id: String(orgId) }
      if (newChannelId) {
        params.channel_id = newChannelId
      }
      setSearchParams(params)
    }
    setPage(1)
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Threads</h1>
        <p className="mt-2 text-sm text-gray-600">View conversation threads for an organization</p>
      </div>

      <div className="mb-6 card">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="form-label">Organization ID</label>
            <input
              type="number"
              value={orgId || ''}
              onChange={(e) => handleOrgIdChange(e.target.value)}
              placeholder="Enter organization ID"
              className="form-input"
              min={1}
            />
          </div>
          <div>
            <label className="form-label">Channel ID (Optional)</label>
            <input
              type="text"
              value={channelId}
              onChange={(e) => handleChannelIdChange(e.target.value)}
              placeholder="e.g., C01234567"
              className="form-input"
            />
          </div>
        </div>
      </div>

      {!orgId ? (
        <div className="text-center py-12 bg-white rounded-lg shadow">
          <p className="text-gray-500">Enter an organization ID to view threads</p>
        </div>
      ) : isLoading ? (
        <LoadingSpinner />
      ) : error ? (
        <ErrorMessage error={error} message="Failed to load threads" />
      ) : data?.threads && data.threads.length > 0 ? (
        <>
          <ThreadsTable threads={data.threads} />
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
          <p className="text-gray-500">No threads found for this organization</p>
        </div>
      )}
    </div>
  )
}
