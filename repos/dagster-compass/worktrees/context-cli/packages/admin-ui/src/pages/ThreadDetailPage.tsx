import { useParams, useSearchParams, Link } from 'react-router-dom'
import { useThreadDetail } from '../hooks/useThreadDetail'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { ErrorMessage } from '../components/ErrorMessage'

export function ThreadDetailPage() {
  const { teamId, channelId, threadTs } = useParams<{
    teamId: string
    channelId: string
    threadTs: string
  }>()
  const [searchParams] = useSearchParams()
  const botId = searchParams.get('bot_id') || undefined

  const { data, isLoading, error } = useThreadDetail(teamId, channelId, threadTs, botId)

  return (
    <div>
      <div className="mb-6">
        <Link
          to="/threads"
          className="text-sm text-blue-600 hover:text-blue-800 hover:underline mb-2 inline-block"
        >
          ← Back to Threads
        </Link>
        <h1 className="text-3xl font-bold text-gray-900">Thread Detail</h1>
        {teamId && channelId && threadTs && (
          <div className="mt-2 text-sm text-gray-600 font-mono">
            <div>Team: {teamId}</div>
            <div>Channel: {channelId}</div>
            <div>Thread TS: {threadTs}</div>
            {data?.bot_id && <div>Bot ID: {data.bot_id}</div>}
          </div>
        )}
      </div>

      {isLoading ? (
        <LoadingSpinner />
      ) : error ? (
        <ErrorMessage error={error} message="Failed to load thread detail" />
      ) : data ? (
        <div className="bg-white rounded-lg shadow">
          <div className="p-6" dangerouslySetInnerHTML={{ __html: data.html }} />
        </div>
      ) : (
        <div className="text-center py-12 bg-white rounded-lg shadow">
          <p className="text-gray-500">Thread not found</p>
        </div>
      )}
    </div>
  )
}
