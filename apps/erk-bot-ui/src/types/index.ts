// Session types
export interface Session {
  session_id: string;
  external_id: string | null;
  working_directory: string;
  status: 'active' | 'processing' | 'error';
  created_at: string;
  last_activity: string;
  message_count: number;
}

export interface StreamEvent {
  event_type: 'text' | 'tool' | 'done' | 'error';
  data: Record<string, string | number | boolean>;
}

// API request types
export interface CreateSessionRequest {
  external_id?: string;
  working_directory: string;
}

export interface SendMessageRequest {
  content: string;
  timeout_seconds?: number;
}

// API response types
export interface SessionListResponse {
  sessions: Session[];
}
