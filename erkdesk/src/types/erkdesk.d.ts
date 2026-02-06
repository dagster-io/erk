export interface WebViewBounds {
  x: number;
  y: number;
  width: number;
  height: number;
}

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
}

export interface FetchPlansResult {
  success: boolean;
  plans: PlanRow[];
  count: number;
  error?: string;
}

export interface ActionResult {
  success: boolean;
  stdout: string;
  stderr: string;
  error?: string;
}

export interface ActionOutputEvent {
  stream: "stdout" | "stderr";
  data: string;
}

export interface ActionCompletedEvent {
  success: boolean;
  error?: string;
}

export interface TerminalSummonResult {
  success: boolean;
  pid: number | null;
  error?: string;
}

export interface ErkdeskAPI {
  version: string;
  updateWebViewBounds: (bounds: WebViewBounds) => void;
  loadWebViewURL: (url: string) => void;
  fetchPlans: () => Promise<FetchPlansResult>;
  executeAction: (command: string, args: string[]) => Promise<ActionResult>;
  startStreamingAction: (command: string, args: string[]) => void;
  onActionOutput: (callback: (event: ActionOutputEvent) => void) => void;
  onActionCompleted: (callback: (event: ActionCompletedEvent) => void) => void;
  removeActionListeners: () => void;
  summonTerminal: (planId: number) => Promise<TerminalSummonResult>;
}

declare global {
  interface Window {
    erkdesk: ErkdeskAPI;
  }
}
