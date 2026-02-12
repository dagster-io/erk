import {useCallback, useEffect, useRef, useState} from 'react';

import type {
  ChatMessage,
  ChatMessageContent,
  ServerMessage,
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

  const wsRef = useRef<WebSocket | null>(null);
  const pendingToolsRef = useRef<Map<string, ChatMessageContent>>(new Map());
  const queryStartRef = useRef<number | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

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

  const sendMessage = useCallback((text: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return;
    }

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

    wsRef.current.send(JSON.stringify({type: 'chat_send', text}));
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
    permissionRequest,
    activity,
    commands,
    sendMessage,
    stopGeneration,
    respondToPermission,
  };
}
