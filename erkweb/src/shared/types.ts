// Plan data from `erk exec dash-data`
export interface PlanRow {
  issue_number: number;
  title: string;
  full_title: string;
  issue_url: string | null;
  pr_number: number | null;
  pr_url: string | null;
  pr_display: string;
  pr_state: string | null;
  checks_display: string;
  comments_display: string;
  objective_display: string;
  learn_display_icon: string;
  worktree_name: string;
  local_impl_display: string;
  remote_impl_display: string;
  run_state_display: string;
  exists_locally: boolean;
  run_url: string | null;
  worktree_branch: string | null;
  pr_head_branch: string | null;
  // Additional fields for state detection
  run_status: string | null;
  run_conclusion: string | null;
  log_entries: [string, string, string][];
}

export interface FetchPlansResult {
  success: boolean;
  plans: PlanRow[];
  count: number;
  error?: string;
}

// Server action result
export interface ActionResult {
  success: boolean;
  output?: string;
  error?: string;
}

// Plan lifecycle states
export type PlanState =
  | 'created'
  | 'in-review'
  | 'queued'
  | 'dispatched'
  | 'implementing-remote'
  | 'implementing-local'
  | 'complete'
  | 'no-changes'
  | 'merged-closed';

export interface PlanStateInfo {
  key: PlanState;
  label: string;
}

export const PLAN_STATES: PlanStateInfo[] = [
  {key: 'created', label: 'Created'},
  {key: 'in-review', label: 'In Review'},
  {key: 'queued', label: 'Queued'},
  {key: 'dispatched', label: 'Dispatched'},
  {key: 'implementing-remote', label: 'Implementing (remote)'},
  {key: 'implementing-local', label: 'Implementing (local)'},
  {key: 'complete', label: 'Complete'},
  {key: 'no-changes', label: 'No Changes'},
  {key: 'merged-closed', label: 'Merged / Closed'},
];

/**
 * Derive the lifecycle state of a plan from its PlanRow data.
 */
export function derivePlanState(plan: PlanRow): PlanState {
  // Merged or closed
  if (plan.pr_state === 'MERGED' || plan.pr_state === 'CLOSED') {
    return 'merged-closed';
  }

  // PR exists and is open
  if (plan.pr_state === 'OPEN') {
    // Check for no-changes (run completed with no diff)
    if (plan.run_conclusion === 'failure' && plan.run_state_display.includes('no-changes')) {
      return 'no-changes';
    }
    // PR is ready (not draft) = complete
    return 'complete';
  }

  // Remote implementation in progress
  if (plan.run_status === 'in_progress') {
    return 'implementing-remote';
  }

  // Local implementation in progress
  if (plan.local_impl_display && plan.local_impl_display !== '-') {
    return 'implementing-local';
  }

  // Dispatched: has workflow-started log entry
  const hasWorkflowStarted = plan.log_entries.some(
    ([event]) => event === 'workflow-started' || event === 'workflow_started',
  );
  if (hasWorkflowStarted && plan.run_status === 'queued') {
    return 'dispatched';
  }

  // Queued: has submission-queued log entry
  const hasSubmissionQueued = plan.log_entries.some(
    ([event]) => event === 'submission-queued' || event === 'submission_queued',
  );
  if (hasSubmissionQueued) {
    return 'queued';
  }

  // TODO: In Review detection requires plan-header metadata parsing
  // For now, skip this state

  return 'created';
}
