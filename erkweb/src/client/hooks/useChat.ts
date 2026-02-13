import {useCallback, useEffect, useRef, useState} from 'react';

import type {
  ChatMessage,
  ChatMessageContent,
  ServerMessage,
  SessionInfo,
  SlashCommandInfo,
} from '../../shared/types.js';

export interface PermissionRequest {
  toolUseId: string;
  toolName: string;
  toolInput: Record<string, unknown>;
  reason?: string;
  hasSuggestions: boolean;
}

export interface ActivityStatus {
  type: 'thinking' | 'tool';
  toolName?: string;
  elapsedSeconds: number;
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streamingText, setStreamingText] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [model, setModel] = useState<string | null>(null);
  const [permissionRequest, setPermissionRequest] = useState<PermissionRequest | null>(null);
  const [activity, setActivity] = useState<ActivityStatus | null>(null);
  const [commands, setCommands] = useState<SlashCommandInfo[]>([]);

  const [chatBranch, setChatBranch] = useState<string | null>(null);
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [sessionsLoading, setSessionsLoading] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const pendingToolsRef = useRef<Map<string, ChatMessageContent>>(new Map());
  const queryStartRef = useRef<number | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const defaultCwdRef = useRef<string | null>(null);
  const selectedSessionIdRef = useRef<string | null>(null);

  // Tick the elapsed timer every second while streaming
  useEffect(() => {
    if (isStreaming) {
      queryStartRef.current = Date.now();
      timerRef.current = setInterval(() => {
        setActivity((prev) => {
          if (!prev) {
            const elapsed = queryStartRef.current ? (Date.now() - queryStartRef.current) / 1000 : 0;
            return {type: 'thinking', elapsedSeconds: elapsed};
          }
          if (prev.type === 'thinking') {
            const elapsed = queryStartRef.current
              ? (Date.now() - queryStartRef.current) / 1000
              : prev.elapsedSeconds + 1;
            return {...prev, elapsedSeconds: elapsed};
          }
          return prev;
        });
      }, 1000);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      queryStartRef.current = null;
    }
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [isStreaming]);

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/chat`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const msg: ServerMessage = JSON.parse(event.data);

      switch (msg.type) {
        case 'chat_init':
          setSessionId(msg.sessionId);
          setModel(msg.model);
          setSelectedSessionId(msg.sessionId);
          selectedSessionIdRef.current = msg.sessionId;
          break;

        case 'chat_commands':
          setCommands(msg.commands);
          break;

        case 'chat_partial':
          setStreamingText((prev) => prev + msg.text);
          // While receiving text, we're in "thinking" mode
          setActivity((prev) => {
            if (!prev || prev.type !== 'thinking') {
              const elapsed = queryStartRef.current
                ? (Date.now() - queryStartRef.current) / 1000
                : 0;
              return {type: 'thinking', elapsedSeconds: elapsed};
            }
            return prev;
          });
          break;

        case 'chat_text':
          // Finalize streaming text into a message
          setStreamingText('');
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (last?.role === 'assistant') {
              // Append text to existing assistant message
              return [
                ...prev.slice(0, -1),
                {
                  ...last,
                  content: [...last.content, {type: 'text' as const, text: msg.fullText}],
                },
              ];
            }
            return [
              ...prev,
              {
                role: 'assistant',
                content: [{type: 'text' as const, text: msg.fullText}],
                timestamp: Date.now(),
              },
            ];
          });
          break;

        case 'chat_tool_use': {
          const toolContent: ChatMessageContent = {
            type: 'tool_use',
            toolName: msg.toolName,
            toolInput: msg.toolInput,
            toolUseId: msg.toolUseId,
          };
          pendingToolsRef.current.set(msg.toolUseId, toolContent);
          setActivity({type: 'tool', toolName: msg.toolName, elapsedSeconds: 0});
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (last?.role === 'assistant') {
              return [
                ...prev.slice(0, -1),
                {
                  ...last,
                  content: [...last.content, toolContent],
                },
              ];
            }
            return [
              ...prev,
              {
                role: 'assistant',
                content: [toolContent],
                timestamp: Date.now(),
              },
            ];
          });
          break;
        }

        case 'chat_tool_result': {
          const resultContent: ChatMessageContent = {
            type: 'tool_result',
            toolUseId: msg.toolUseId,
            output: msg.output,
            isError: msg.isError,
          };
          // Attach result to the tool_use in the last assistant message
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (last?.role === 'assistant') {
              return [
                ...prev.slice(0, -1),
                {
                  ...last,
                  content: [...last.content, resultContent],
                },
              ];
            }
            return prev;
          });
          pendingToolsRef.current.delete(msg.toolUseId);
          // Return to thinking state after tool completes
          setActivity((prev) => {
            if (prev?.type === 'tool') {
              const elapsed = queryStartRef.current
                ? (Date.now() - queryStartRef.current) / 1000
                : 0;
              return {type: 'thinking', elapsedSeconds: elapsed};
            }
            return prev;
          });
          break;
        }

        case 'chat_tool_progress':
          setActivity({type: 'tool', toolName: msg.toolName, elapsedSeconds: msg.elapsedSeconds});
          break;

        case 'permission_request':
          setPermissionRequest({
            toolUseId: msg.toolUseId,
            toolName: msg.toolName,
            toolInput: msg.toolInput,
            reason: msg.reason,
            hasSuggestions: msg.hasSuggestions,
          });
          break;

        case 'chat_done':
          setIsStreaming(false);
          setStreamingText('');
          setPermissionRequest(null);
          setActivity(null);
          break;

        case 'chat_error':
          setIsStreaming(false);
          setStreamingText('');
          setPermissionRequest(null);
          setActivity(null);
          setMessages((prev) => [
            ...prev,
            {
              role: 'assistant',
              content: [{type: 'text' as const, text: `Error: ${msg.message}`}],
              timestamp: Date.now(),
            },
          ]);
          break;
      }
    };

    ws.onclose = () => {
      setIsStreaming(false);
      setPermissionRequest(null);
      setActivity(null);
    };

    return () => {
      ws.close();
    };
  }, []);

  const sendMessage = useCallback(
    (text: string, options?: {cwd?: string; newSession?: boolean}) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        return;
      }

      // Consume selected session ID (used once, then cleared)
      const resumeId = selectedSessionIdRef.current;
      selectedSessionIdRef.current = null;
      setSelectedSessionId(null);

      if (options?.newSession || resumeId) {
        setMessages([]);
      }

      // Use default cwd from selected plan if no explicit cwd
      const effectiveCwd = options?.cwd ?? defaultCwdRef.current ?? undefined;

      // Add user message to state
      setMessages((prev) => [
        ...prev,
        {
          role: 'user',
          content: [{type: 'text' as const, text}],
          timestamp: Date.now(),
        },
      ]);

      setIsStreaming(true);
      setStreamingText('');
      setActivity({type: 'thinking', elapsedSeconds: 0});

      wsRef.current.send(
        JSON.stringify({
          type: 'chat_send',
          text,
          cwd: effectiveCwd,
          newSession: options?.newSession,
          resumeSessionId: resumeId ?? undefined,
        }),
      );
    },
    [],
  );

  // Set the default cwd and branch for the chat (driven by plan selection).
  // Fetches recent sessions and auto-loads the most recent one.
  const setChatContext = useCallback((cwd: string | null, branch: string | null) => {
    defaultCwdRef.current = cwd;
    setChatBranch(branch);
    setSelectedSessionId(null);
    selectedSessionIdRef.current = null;
    setMessages([]);
    if (!cwd) {
      setSessions([]);
      setSessionsLoading(false);
      return;
    }
    setSessionsLoading(true);
    const encodedCwd = encodeURIComponent(cwd);
    fetch(`/api/sessions?cwd=${encodedCwd}`)
      .then((res) => res.json())
      .then((data) => {
        if (!data.success) {
          setSessionsLoading(false);
          return;
        }
        setSessions(data.sessions);
        const latest = data.sessions[0];
        if (!latest) {
          setSessionsLoading(false);
          return;
        }
        setSelectedSessionId(latest.session_id);
        selectedSessionIdRef.current = latest.session_id;
        fetch(`/api/sessions/${latest.session_id}/messages?cwd=${encodedCwd}`)
          .then((r) => r.json())
          .then((msgData) => {
            if (msgData.success) {
              setMessages(msgData.messages);
            }
            setSessionsLoading(false);
          })
          .catch(() => setSessionsLoading(false));
      })
      .catch(() => setSessionsLoading(false));
  }, []);

  // Immediately clear messages and show loading before worktree path resolves.
  const setLoading = useCallback((branch: string | null) => {
    setMessages([]);
    setSessions([]);
    setSelectedSessionId(null);
    selectedSessionIdRef.current = null;
    setSessionsLoading(true);
    setChatBranch(branch);
  }, []);

  const selectSession = useCallback((sid: string | null) => {
    setSelectedSessionId(sid);
    selectedSessionIdRef.current = sid;
    if (!sid) {
      setMessages([]);
      return;
    }
    const cwd = defaultCwdRef.current;
    if (!cwd) {
      return;
    }
    fetch(`/api/sessions/${sid}/messages?cwd=${encodeURIComponent(cwd)}`)
      .then((res) => res.json())
      .then((data) => {
        if (data.success) {
          setMessages(data.messages);
        }
      })
      .catch(() => {});
  }, []);

  const stopGeneration = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return;
    }
    wsRef.current.send(JSON.stringify({type: 'chat_stop'}));
  }, []);

  const respondToPermission = useCallback(
    (toolUseId: string, allowed: boolean, applyAlways: boolean) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        return;
      }
      wsRef.current.send(
        JSON.stringify({type: 'permission_response', toolUseId, allowed, applyAlways}),
      );
      setPermissionRequest(null);
    },
    [],
  );

  return {
    messages,
    streamingText,
    isStreaming,
    sessionId,
    model,
    chatBranch,
    sessions,
    selectedSessionId,
    sessionsLoading,
    permissionRequest,
    activity,
    commands,
    sendMessage,
    setChatContext,
    setLoading,
    selectSession,
    stopGeneration,
    respondToPermission,
  };
}
