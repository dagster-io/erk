import { useState } from 'react'
import { useTokens, useCreateToken } from '../hooks/useTokens'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { ErrorMessage } from '../components/ErrorMessage'
import { TokenTable } from '../components/TokenTable'
import { TokenForm } from '../components/TokenForm'

export function TokensPage() {
  const { data, isLoading, error } = useTokens()
  const createToken = useCreateToken()
  const [showForm, setShowForm] = useState(false)

  const handleCreateToken = async (tokenData: {
    token?: string
    is_single_use: boolean
    consumer_bonus_answers: number
  }) => {
    try {
      const result = await createToken.mutateAsync(tokenData)
      if (result.success) {
        alert(`Token created successfully: ${result.token}`)
        setShowForm(false)
      } else {
        alert(`Failed to create token: ${result.error}`)
      }
    } catch (error) {
      alert(`Error creating token: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  if (isLoading) {
    return <LoadingSpinner />
  }

  if (error) {
    return <ErrorMessage error={error} message="Failed to load tokens" />
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Invite Tokens</h1>
          <p className="mt-2 text-sm text-gray-600">
            Create and manage invitation tokens for new organizations
          </p>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="btn btn-primary">
          {showForm ? 'Cancel' : 'Create Token'}
        </button>
      </div>

      {showForm && (
        <div className="mb-6">
          <TokenForm onSubmit={handleCreateToken} isSubmitting={createToken.isPending} />
        </div>
      )}

      {data?.tokens && data.tokens.length > 0 ? (
        <TokenTable tokens={data.tokens} />
      ) : (
        <div className="text-center py-12 bg-white rounded-lg shadow">
          <p className="text-gray-500">No tokens found</p>
        </div>
      )}
    </div>
  )
}
