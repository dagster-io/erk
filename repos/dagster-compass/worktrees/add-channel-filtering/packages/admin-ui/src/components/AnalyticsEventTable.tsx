import { useState } from 'react'
import type { AnalyticsEvent } from '../types/analytics'
import { formatDate } from '../utils/format'

interface AnalyticsEventTableProps {
  events: AnalyticsEvent[]
}

export function AnalyticsEventTable({ events }: AnalyticsEventTableProps) {
  const [expandedEventId, setExpandedEventId] = useState<number | null>(null)

  const toggleExpanded = (eventId: number) => {
    setExpandedEventId(expandedEventId === eventId ? null : eventId)
  }

  const formatMetadata = (metadata: Record<string, unknown> | string) => {
    if (typeof metadata === 'string') {
      try {
        return JSON.stringify(JSON.parse(metadata), null, 2)
      } catch {
        return metadata
      }
    }
    return JSON.stringify(metadata, null, 2)
  }

  return (
    <div className="table-container">
      <table className="data-table">
        <thead>
          <tr>
            <th>Event Type</th>
            <th>Timestamp</th>
            <th>User ID</th>
            <th>Channel ID</th>
            <th>Metadata</th>
          </tr>
        </thead>
        <tbody>
          {events.map((event) => {
            const isExpanded = expandedEventId === event.id
            const hasMetadata =
              event.metadata &&
              (typeof event.metadata === 'string'
                ? event.metadata.length > 0
                : Object.keys(event.metadata).length > 0)

            return (
              <>
                <tr key={event.id}>
                  <td>
                    <span className="badge bg-blue-100 text-blue-800">{event.event_type}</span>
                  </td>
                  <td className="text-sm text-gray-600">{formatDate(event.event_timestamp)}</td>
                  <td className="font-mono text-xs">
                    {event.user_id ? (
                      <span className="text-gray-700">{event.user_id}</span>
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
                  </td>
                  <td className="font-mono text-xs">
                    {event.channel_id ? (
                      <span className="text-gray-700">{event.channel_id}</span>
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
                  </td>
                  <td>
                    {hasMetadata ? (
                      <button
                        onClick={() => toggleExpanded(event.id)}
                        className="text-sm text-blue-600 hover:text-blue-800"
                      >
                        {isExpanded ? 'Hide' : 'Show'} metadata
                      </button>
                    ) : (
                      <span className="text-gray-400 text-sm">-</span>
                    )}
                  </td>
                </tr>
                {isExpanded && hasMetadata && (
                  <tr>
                    <td colSpan={5} className="bg-gray-50 p-4">
                      <div className="text-xs">
                        <div className="font-medium text-gray-700 mb-2">Event Metadata:</div>
                        <pre className="bg-white p-3 rounded border border-gray-200 overflow-x-auto">
                          <code className="text-gray-800">{formatMetadata(event.metadata)}</code>
                        </pre>
                      </div>
                    </td>
                  </tr>
                )}
              </>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
