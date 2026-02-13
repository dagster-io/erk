// WebSocket protocol messages

// Client → Server
export type ClientMessage =
  | {type: 'chat_send'; text: string; cwd?: string; newSession?: boolean; resumeSessionId?: string}
  | {type: 'chat_stop'}
  | {type: 'permission_response'; toolUseId: string; allowed: boolean; applyAlways: boolean};

// Server → Client
export type ServerMessage =
  | {type: 'chat_init'; sessionId: string; model: string}
  | {type: 'chat_partial'; text: string}
  | {type: 'chat_text'; fullText: string}
  | {
      type: 'chat_tool_use';
      toolName: string;
      toolInput: Record<string, unknown>;
      toolUseId: string;
    }
  | {
      type: 'chat_tool_result';
      toolUseId: string;
      output: string;
      isError: boolean;
    }
  | {type: 'chat_tool_progress'; toolUseId: string; toolName: string; elapsedSeconds: number}
  | {type: 'chat_done'; numTurns: number; costUsd: number}
  | {type: 'chat_error'; message: string}
  | {
      type: 'permission_request';
      toolUseId: string;
      toolName: string;
      toolInput: Record<string, unknown>;
      reason?: string;
      hasSuggestions: boolean;
    }
  | {
      type: 'chat_commands';
      commands: SlashCommandInfo[];
    };

export interface SlashCommandInfo {
  name: string;
  description: string;
  argumentHint: string;
}

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
}

export interface FetchPlansResult {
  success: boolean;
  plans: PlanRow[];
  count: number;
  error?: string;
}

// Session info from `erk exec list-sessions`
export interface SessionInfo {
  session_id: string;
  mtime_relative: string;
  summary: string;
  branch: string | null;
}

// Chat message for UI state
export interface ChatMessageContent {
  type: 'text' | 'tool_use' | 'tool_result';
  text?: string;
  toolName?: string;
  toolInput?: Record<string, unknown>;
  toolUseId?: string;
  output?: string;
  isError?: boolean;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: ChatMessageContent[];
  timestamp: number;
}
