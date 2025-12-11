import { useState } from 'react'
import type { OnboardingState } from '../types/onboarding'
import { useOnboardingDetails } from '../hooks/useOnboarding'
import { formatShortDate } from '../utils/format'

interface OnboardingTableProps {
  states: OnboardingState[]
}

export function OnboardingTable({ states }: OnboardingTableProps) {
  const [expandedOrgId, setExpandedOrgId] = useState<number | null>(null)

  return (
    <div className="space-y-4">
      {states.map((state) => (
        <OnboardingCard
          key={state.organization_id}
          state={state}
          isExpanded={expandedOrgId === state.organization_id}
          onToggle={() =>
            setExpandedOrgId(expandedOrgId === state.organization_id ? null : state.organization_id)
          }
        />
      ))}
    </div>
  )
}

interface OnboardingCardProps {
  state: OnboardingState
  isExpanded: boolean
  onToggle: () => void
}

function OnboardingCard({ state, isExpanded, onToggle }: OnboardingCardProps) {
  const { data: details, isLoading } = useOnboardingDetails(
    isExpanded ? state.organization_id : null
  )

  const getStatusBadge = (status: string) => {
    const classes = {
      Complete: 'badge bg-green-100 text-green-800',
      Incomplete: 'badge bg-yellow-100 text-yellow-800',
      Error: 'badge bg-red-100 text-red-800',
    }
    return <span className={classes[status as keyof typeof classes] || 'badge'}>{status}</span>
  }

  const renderSteps = (
    steps: Record<string, { completed: boolean; completed_at: string | null }>
  ) => {
    return Object.entries(steps).map(([key, step]) => (
      <div key={key} className="flex items-center justify-between py-2 border-b border-gray-100">
        <div className="flex items-center space-x-2">
          {step.completed ? (
            <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                clipRule="evenodd"
              />
            </svg>
          ) : (
            <svg className="w-5 h-5 text-gray-300" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm0-2a6 6 0 100-12 6 6 0 000 12z"
                clipRule="evenodd"
              />
            </svg>
          )}
          <span className="text-sm">{key.replace(/_/g, ' ')}</span>
        </div>
        {step.completed_at && (
          <span className="text-xs text-gray-500">{formatShortDate(step.completed_at)}</span>
        )}
      </div>
    ))
  }

  return (
    <div className="bg-white rounded-lg shadow">
      <button
        onClick={onToggle}
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center space-x-4">
          <span className="font-medium text-gray-900">{state.organization_name}</span>
          <span className="text-sm text-gray-500">ID: {state.organization_id}</span>
          {getStatusBadge(state.setup_status)}
        </div>
        <svg
          className={`w-5 h-5 text-gray-400 transform transition-transform ${
            isExpanded ? 'rotate-180' : ''
          }`}
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path
            fillRule="evenodd"
            d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {isExpanded && (
        <div className="px-6 pb-4 border-t border-gray-200">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-4">
            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-2">Initial Setup</h3>
              {renderSteps(state.initial_setup_steps)}
            </div>

            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-2">Usage Milestones</h3>
              {renderSteps(state.usage_milestones)}
            </div>

            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-2">Error Events</h3>
              {Object.keys(state.error_events).length > 0 ? (
                renderSteps(state.error_events)
              ) : (
                <p className="text-sm text-gray-500 py-2">No errors</p>
              )}
            </div>
          </div>

          {isLoading && (
            <div className="mt-4 text-center text-sm text-gray-500">Loading details...</div>
          )}

          {details && (
            <div className="mt-4 p-4 bg-gray-50 rounded-lg">
              <h3 className="text-sm font-medium text-gray-900 mb-2">Analytics Summary</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">Total Events:</span>
                  <span className="ml-2 font-medium">{details.analytics_summary.total_events}</span>
                </div>
                <div>
                  <span className="text-gray-500">Event Types:</span>
                  <span className="ml-2 font-medium">
                    {details.analytics_summary.event_types.length}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500">First Event:</span>
                  <span className="ml-2 font-medium">
                    {formatShortDate(details.analytics_summary.first_event)}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500">Last Event:</span>
                  <span className="ml-2 font-medium">
                    {formatShortDate(details.analytics_summary.last_event)}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
