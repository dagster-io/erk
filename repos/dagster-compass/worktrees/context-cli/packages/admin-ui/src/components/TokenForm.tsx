import { useState } from 'react'

interface TokenFormProps {
  onSubmit: (data: {
    token?: string
    is_single_use: boolean
    consumer_bonus_answers: number
  }) => void
  isSubmitting: boolean
}

export function TokenForm({ onSubmit, isSubmitting }: TokenFormProps) {
  const [token, setToken] = useState('')
  const [bonusAnswers, setBonusAnswers] = useState(150)
  const [isMultiUse, setIsMultiUse] = useState(true)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit({
      token: token.trim() || undefined,
      is_single_use: !isMultiUse,
      consumer_bonus_answers: bonusAnswers,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="card">
      <h2 className="text-xl font-semibold mb-4">Create New Token</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="form-label">Token (optional - auto-generated if empty)</label>
          <input
            type="text"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="Leave empty for UUID or enter custom token"
            className="form-input"
            maxLength={20}
          />
          <p className="mt-1 text-xs text-gray-500">
            Custom tokens must be uppercase, max 20 characters
          </p>
        </div>

        <div>
          <label className="form-label">Bonus Answers</label>
          <input
            type="number"
            value={bonusAnswers}
            onChange={(e) => setBonusAnswers(Number(e.target.value))}
            min={0}
            className="form-input"
          />
        </div>
      </div>

      <div className="mt-4">
        <label className="flex items-center space-x-2">
          <input
            type="checkbox"
            checked={isMultiUse}
            onChange={(e) => setIsMultiUse(e.target.checked)}
            className="form-checkbox"
          />
          <span className="text-sm font-medium text-gray-700">
            Multi-use token (can be used by multiple organizations)
          </span>
        </label>
      </div>

      <div className="mt-6 flex justify-end">
        <button type="submit" disabled={isSubmitting} className="btn btn-primary">
          {isSubmitting ? 'Creating...' : 'Create Token'}
        </button>
      </div>
    </form>
  )
}
