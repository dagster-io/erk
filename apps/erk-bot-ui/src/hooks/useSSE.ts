import { useState, useCallback, useRef } from 'react';
import type { StreamEvent } from '../types';
import { sendMessage } from '../api/sessions';

export interface UseSSEResult {
  events: StreamEvent[];
  isStreaming: boolean;
  send: (content: string) => () => void;
  clear: () => void;
}

export function useSSE(sessionId: string): UseSSEResult {
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const controllerRef = useRef<AbortController | null>(null);

  const send = useCallback(
    (content: string) => {
      // Cancel any existing request
      if (controllerRef.current) {
        controllerRef.current.abort();
      }

      setIsStreaming(true);
      setEvents([]);

      const controller = sendMessage(
        sessionId,
        { content },
        (event) => {
          setEvents((prev) => [...prev, event]);
          if (event.event_type === 'done' || event.event_type === 'error') {
            setIsStreaming(false);
            controllerRef.current = null;
          }
        }
      );

      controllerRef.current = controller;

      return () => {
        controller.abort();
        setIsStreaming(false);
        controllerRef.current = null;
      };
    },
    [sessionId]
  );

  const clear = useCallback(() => {
    setEvents([]);
  }, []);

  return { events, isStreaming, send, clear };
}
