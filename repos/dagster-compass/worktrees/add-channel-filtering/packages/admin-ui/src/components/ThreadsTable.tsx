import { Link } from 'react-router-dom'
import type { Thread } from '../types/threads'

interface ThreadsTableProps {
  threads: Thread[]
}

export function ThreadsTable({ threads }: ThreadsTableProps) {
  // Extract team_id from bot_id (format: "T01234567-channel-name")
  const getTeamId = (botId: string): string => {
    const parts = botId.split('-')
    return parts[0] || ''
  }

  // Build the thread viewer URL with bot_id as query param
  const getThreadUrl = (thread: Thread): string => {
    const teamId = getTeamId(thread.bot_id)
    return `/thread/${teamId}/${thread.channel_id}/${thread.thread_ts}?bot_id=${encodeURIComponent(thread.bot_id)}`
  }

  return (
    <div className="table-container">
      <table className="data-table">
        <thead>
          <tr>
            <th>Bot ID</th>
            <th>Channel ID</th>
            <th>Thread TS</th>
            <th>Event Count</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {threads.map((thread, index) => {
            const threadUrl = getThreadUrl(thread)

            return (
              <tr key={`${thread.bot_id}-${thread.channel_id}-${thread.thread_ts}-${index}`}>
                <td className="font-mono text-xs">
                  <span className="text-gray-700">{thread.bot_id}</span>
                </td>
                <td className="font-mono text-xs">
                  <span className="text-gray-700">{thread.channel_id}</span>
                </td>
                <td className="font-mono text-xs">
                  <span className="text-gray-700">{thread.thread_ts}</span>
                </td>
                <td>
                  <span className="badge bg-blue-100 text-blue-800">{thread.event_count}</span>
                </td>
                <td>
                  <Link
                    to={threadUrl}
                    className="text-sm text-blue-600 hover:text-blue-800 hover:underline"
                  >
                    View Thread
                  </Link>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
