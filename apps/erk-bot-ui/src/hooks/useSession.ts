import { useState, useEffect, useCallback } from 'react';
import type { Session } from '../types';
import { getSession, listSessions, createSession, deleteSession } from '../api/sessions';

export interface UseSessionResult {
  sessions: Session[];
  currentSession: Session | null;
  isLoading: boolean;
  error: string | null;
  loadSessions: () => Promise<void>;
  selectSession: (sessionId: string) => Promise<void>;
  createNewSession: (workingDirectory: string, externalId?: string) => Promise<Session>;
  removeSession: (sessionId: string) => Promise<void>;
}

export function useSession(): UseSessionResult {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSession, setCurrentSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSessions = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await listSessions();
      setSessions(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load sessions');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const selectSession = useCallback(async (sessionId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const session = await getSession(sessionId);
      setCurrentSession(session);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load session');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const createNewSession = useCallback(
    async (workingDirectory: string, externalId?: string): Promise<Session> => {
      setIsLoading(true);
      setError(null);
      try {
        const session = await createSession({
          working_directory: workingDirectory,
          external_id: externalId,
        });
        setSessions((prev) => [session, ...prev]);
        setCurrentSession(session);
        return session;
      } catch (e) {
        const message = e instanceof Error ? e.message : 'Failed to create session';
        setError(message);
        throw new Error(message);
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const removeSession = useCallback(async (sessionId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      await deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
      if (currentSession?.session_id === sessionId) {
        setCurrentSession(null);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to delete session');
    } finally {
      setIsLoading(false);
    }
  }, [currentSession?.session_id]);

  // Load sessions on mount
  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  return {
    sessions,
    currentSession,
    isLoading,
    error,
    loadSessions,
    selectSession,
    createNewSession,
    removeSession,
  };
}
