import {useEffect, useRef, useState} from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import {ChatInput} from './ChatInput.js';
import {ChatMessage} from './ChatMessage.js';
import {PermissionPrompt} from './PermissionPrompt.js';
import type {
  ChatMessage as ChatMessageType,
  SessionInfo,
  SlashCommandInfo,
} from '../../shared/types.js';
import type {ActivityStatus, PermissionRequest} from '../hooks/useChat.js';
import './ChatPanel.css';

/** Throttle streaming text so ReactMarkdown only re-parses every ~100ms. */
function useThrottledValue(value: string, ms: number): string {
  const [throttled, setThrottled] = useState(value);
  const lastRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const now = Date.now();
    if (now - lastRef.current >= ms) {
      lastRef.current = now;
      setThrottled(value);
      return;
    }
    timerRef.current = setTimeout(
      () => {
        lastRef.current = Date.now();
        setThrottled(value);
      },
      ms - (now - lastRef.current),
    );
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [value, ms]);

  // Flush immediately when value clears (stream ended)
  useEffect(() => {
    if (!value) setThrottled('');
  }, [value]);

  return throttled;
}

function formatElapsed(seconds: number): string {
  const s = Math.floor(seconds);
  if (s < 60) {
    return `${s}s`;
  }
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return `${m}m ${rem}s`;
}

function summarizeSession(s: SessionInfo): string {
  if (s.summary) {
    const clean = s.summary.replace(/<[^>]+>/g, '').trim();
    return clean.length > 50 ? clean.slice(0, 50) + '...' : clean;
  }
  return s.session_id.slice(0, 8);
}

interface ChatPanelProps {
  messages: ChatMessageType[];
  streamingText: string;
  isStreaming: boolean;
  sessionId: string | null;
  model: string | null;
  chatBranch: string | null;
  sessions: SessionInfo[];
  selectedSessionId: string | null;
  sessionsLoading: boolean;
  permissionRequest: PermissionRequest | null;
  activity: ActivityStatus | null;
  commands: SlashCommandInfo[];
  onSend: (text: string) => void;
  onStop: () => void;
  onSelectSession: (sessionId: string | null) => void;
  onPermissionRespond: (toolUseId: string, allowed: boolean, applyAlways: boolean) => void;
}

export function ChatPanel({
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
  onSend,
  onStop,
  onSelectSession,
  onPermissionRespond,
}: ChatPanelProps) {
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const isNearBottomRef = useRef(true);
  const throttledStreamingText = useThrottledValue(streamingText, 100);

  const handleScroll = () => {
    const container = messagesContainerRef.current;
    if (!container) {
      return;
    }
    const threshold = 100;
    isNearBottomRef.current =
      container.scrollHeight - container.scrollTop - container.clientHeight < threshold;
  };

  useEffect(() => {
    if (isNearBottomRef.current) {
      messagesEndRef.current?.scrollIntoView({behavior: 'instant'});
    }
  }, [messages, streamingText, permissionRequest, activity]);

  useEffect(() => {
    const container = messagesContainerRef.current;
    if (!container) {
      return;
    }
    const observer = new MutationObserver(() => {
      if (isNearBottomRef.current) {
        messagesEndRef.current?.scrollIntoView({behavior: 'instant'});
      }
    });
    observer.observe(container, {childList: true, subtree: true, attributes: true});
    return () => observer.disconnect();
  }, []);

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <span className="chat-title">Chat</span>
        {chatBranch && (
          <span className="chat-branch" title={chatBranch}>
            {chatBranch}
          </span>
        )}
        {sessions.length > 0 && (
          <select
            className="session-picker"
            value={selectedSessionId ?? ''}
            onChange={(e) => onSelectSession(e.target.value || null)}
            disabled={isStreaming}
          >
            <option value="">New session</option>
            {sessions.map((s) => (
              <option key={s.session_id} value={s.session_id}>
                {s.mtime_relative} - {summarizeSession(s)}
              </option>
            ))}
          </select>
        )}
        {model && <span className="chat-model">{model}</span>}
        {sessionId && (
          <span className="chat-session" title={sessionId}>
            {sessionId.slice(0, 8)}
          </span>
        )}
      </div>

      <div
        className={`chat-messages${sessionsLoading ? ' loading' : ''}`}
        ref={messagesContainerRef}
        onScroll={handleScroll}
      >
        {messages.map((msg, i) => (
          <ChatMessage key={i} message={msg} />
        ))}
        {throttledStreamingText && (
          <div className="chat-message assistant streaming">
            <div className="message-role">Claude</div>
            <div className="message-content">
              <div className="text-block">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{throttledStreamingText}</ReactMarkdown>
              </div>
            </div>
          </div>
        )}
        {permissionRequest && (
          <PermissionPrompt request={permissionRequest} onRespond={onPermissionRespond} />
        )}
        <div ref={messagesEndRef} />
      </div>

      {activity && (
        <div className="activity-bar">
          <span className="activity-spinner" />
          <span className="activity-label">
            {activity.type === 'thinking' ? 'Thinking...' : `Running ${activity.toolName}...`}
          </span>
          <span className="activity-elapsed">{formatElapsed(activity.elapsedSeconds)}</span>
        </div>
      )}

      <ChatInput isStreaming={isStreaming} commands={commands} onSend={onSend} onStop={onStop} />
    </div>
  );
}
