import { useOnboardingStates } from '../hooks/useOnboarding'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { ErrorMessage } from '../components/ErrorMessage'
import { OnboardingTable } from '../components/OnboardingTable'

export function OnboardingPage() {
  const { data, isLoading, error } = useOnboardingStates(100)

  if (isLoading) {
    return <LoadingSpinner />
  }

  if (error) {
    return <ErrorMessage error={error} message="Failed to load onboarding states" />
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Onboarding Progress</h1>
        <p className="mt-2 text-sm text-gray-600">
          Track onboarding setup and usage milestones for all organizations
        </p>
      </div>

      {data?.states && data.states.length > 0 ? (
        <OnboardingTable states={data.states} />
      ) : (
        <div className="text-center py-12 bg-white rounded-lg shadow">
          <p className="text-gray-500">No onboarding states found</p>
        </div>
      )}
    </div>
  )
}
