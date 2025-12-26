export interface OnboardingState {
  organization_id: number
  organization_name: string
  setup_status: 'Complete' | 'Incomplete' | 'Error'
  initial_setup_steps: Record<string, OnboardingStep>
  usage_milestones: Record<string, OnboardingStep>
  error_events: Record<string, OnboardingStep>
}

export interface OnboardingStep {
  completed: boolean
  completed_at: string | null
}

export interface OnboardingDetails {
  analytics_summary: {
    total_events: number
    event_types: string[]
    first_event: string | null
    last_event: string | null
  }
}

export interface OnboardingResponse {
  states: OnboardingState[]
}
