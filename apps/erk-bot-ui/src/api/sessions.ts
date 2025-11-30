import type {
  Session,
  StreamEvent,
  CreateSessionRequest,
  SendMessageRequest,
  SessionListResponse,
} from '../types';

const API_BASE = '/api';

export async function createSession(req: CreateSessionRequest): Promise<Session> {
  const res = await fetch(`${API_BASE}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    throw new Error(`Failed to create session: ${res.statusText}`);
  }
  return res.json();
}

export async function listSessions(): Promise<Session[]> {
  const res = await fetch(`${API_BASE}/sessions`);
  if (!res.ok) {
    throw new Error(`Failed to list sessions: ${res.statusText}`);
  }
  const data: SessionListResponse = await res.json();
  return data.sessions;
}

export async function getSession(sessionId: string): Promise<Session> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}`);
  if (!res.ok) {
    throw new Error(`Failed to get session: ${res.statusText}`);
  }
  return res.json();
}

export async function deleteSession(sessionId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}`, { method: 'DELETE' });
  if (!res.ok) {
    throw new Error(`Failed to delete session: ${res.statusText}`);
  }
}

export function sendMessage(
  sessionId: string,
  req: SendMessageRequest,
  onEvent: (event: StreamEvent) => void,
): AbortController {
  const controller = new AbortController();

  fetch(`${API_BASE}/sessions/${sessionId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
    signal: controller.signal,
  }).then(async (res) => {
    const reader = res.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) return;

    let buffer = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Parse SSE format: "event: type\ndata: {...}\n\n"
      const parts = buffer.split('\n\n');
      buffer = parts.pop() || ''; // Keep incomplete part in buffer

      for (const part of parts) {
        if (!part.trim()) continue;

        const lines = part.split('\n');
        let eventType = '';
        let data = '';

        for (const line of lines) {
          if (line.startsWith('event:')) {
            eventType = line.slice(6).trim();
          } else if (line.startsWith('data:')) {
            data = line.slice(5).trim();
          }
        }

        if (eventType && data) {
          try {
            const parsedData = JSON.parse(data);
            onEvent({
              event_type: eventType as StreamEvent['event_type'],
              data: parsedData,
            });
          } catch (e) {
            console.error('Failed to parse SSE data:', e);
          }
        }
      }
    }
  }).catch((err) => {
    if (err.name !== 'AbortError') {
      console.error('Stream error:', err);
      onEvent({
        event_type: 'error',
        data: { message: err.message || 'Unknown error' },
      });
    }
  });

  return controller;
}
