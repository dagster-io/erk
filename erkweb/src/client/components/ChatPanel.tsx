import {type KeyboardEvent, useEffect, useMemo, useRef, useState} from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import {ChatMessage} from './ChatMessage.js';
import {CommandTypeahead, filterCommands} from './CommandTypeahead.js';
import {PermissionPrompt} from './PermissionPrompt.js';
import type {ChatMessage as ChatMessageType, SlashCommandInfo} from '../../shared/types.js';
import type {ActivityStatus, PermissionRequest} from '../hooks/useChat.js';
import './ChatPanel.css';

function formatElapsed(seconds: number): string {
  const s = Math.floor(seconds);
  if (s < 60) {
    return `${s}s`;
  }
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return `${m}m ${rem}s`;
}

interface ChatPanelProps {
  messages: ChatMessageType[];
  streamingText: string;
  isStreaming: boolean;
  sessionId: string | null;
  model: string | null;
  permissionRequest: PermissionRequest | null;
  activity: ActivityStatus | null;
  commands: SlashCommandInfo[];
  onSend: (text: string) => void;
  onStop: () => void;
  onPermissionRespond: (toolUseId: string, allowed: boolean, applyAlways: boolean) => void;
}

export function ChatPanel({
  messages,
  streamingText,
  isStreaming,
  sessionId,
  model,
  permissionRequest,
  activity,
  commands,
  onSend,
  onStop,
  onPermissionRespond,
}: ChatPanelProps) {
  const [input, setInput] = useState('');
  const [typeaheadIndex, setTypeaheadIndex] = useState(0);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isNearBottomRef = useRef(true);

  // Determine if typeahead should be shown
  const slashMatch = /^\/(\S*)$/.exec(input);
  const showTypeahead = slashMatch !== null && commands.length > 0 && !isStreaming;
  const typeaheadFilter = slashMatch ? slashMatch[1] : '';
  const filteredCommands = useMemo(
    () => (showTypeahead ? filterCommands(commands, typeaheadFilter) : []),
    [commands, typeaheadFilter, showTypeahead],
  );

  // Reset index when filter changes
  useEffect(() => {
    setTypeaheadIndex(0);
  }, [typeaheadFilter]);

  // Track whether user is near the bottom of the scroll container
  const handleScroll = () => {
    const container = messagesContainerRef.current;
    if (!container) {
      return;
    }
    const threshold = 100;
    isNearBottomRef.current =
      container.scrollHeight - container.scrollTop - container.clientHeight < threshold;
  };

  // Auto-scroll when content changes, but only if user was already near bottom
  useEffect(() => {
    if (isNearBottomRef.current) {
      messagesEndRef.current?.scrollIntoView({behavior: 'smooth'});
    }
  }, [messages, streamingText, permissionRequest, activity]);

  // Observe DOM mutations (e.g. tool blocks expanding) to keep scroll pinned
  useEffect(() => {
    const container = messagesContainerRef.current;
    if (!container) {
      return;
    }
    const observer = new MutationObserver(() => {
      if (isNearBottomRef.current) {
        messagesEndRef.current?.scrollIntoView({behavior: 'smooth'});
      }
    });
    observer.observe(container, {childList: true, subtree: true, attributes: true});
    return () => observer.disconnect();
  }, []);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = 'auto';
      ta.style.height = Math.min(ta.scrollHeight, 200) + 'px';
    }
  }, [input]);

  const selectCommand = (cmd: SlashCommandInfo) => {
    setInput(`/${cmd.name} `);
    textareaRef.current?.focus();
  };

  const handleSend = () => {
    const text = input.trim();
    if (!text || isStreaming) {
      return;
    }
    onSend(text);
    setInput('');
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (showTypeahead && filteredCommands.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setTypeaheadIndex((prev) => Math.min(prev + 1, filteredCommands.length - 1));
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setTypeaheadIndex((prev) => Math.max(prev - 1, 0));
        return;
      }
      if (e.key === 'Tab' || (e.key === 'Enter' && !e.shiftKey)) {
        e.preventDefault();
        selectCommand(filteredCommands[typeaheadIndex]);
        return;
      }
      if (e.key === 'Escape') {
        e.preventDefault();
        setInput('');
        return;
      }
    }

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <span className="chat-title">Chat</span>
        {model && <span className="chat-model">{model}</span>}
        {sessionId && (
          <span className="chat-session" title={sessionId}>
            {sessionId.slice(0, 8)}
          </span>
        )}
      </div>

      <div className="chat-messages" ref={messagesContainerRef} onScroll={handleScroll}>
        {messages.map((msg, i) => (
          <ChatMessage key={i} message={msg} />
        ))}
        {streamingText && (
          <div className="chat-message assistant streaming">
            <div className="message-role">Claude</div>
            <div className="message-content">
              <div className="text-block">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{streamingText}</ReactMarkdown>
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

      <div className="chat-input-area">
        {showTypeahead && filteredCommands.length > 0 && (
          <CommandTypeahead
            commands={filteredCommands}
            filter={typeaheadFilter}
            selectedIndex={typeaheadIndex}
            onSelect={selectCommand}
          />
        )}
        <textarea
          ref={textareaRef}
          className="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Send a message... (Enter to send, Shift+Enter for newline)"
          rows={1}
          disabled={isStreaming}
        />
        {isStreaming ? (
          <button className="chat-btn stop-btn" onClick={onStop}>
            Stop
          </button>
        ) : (
          <button className="chat-btn send-btn" onClick={handleSend} disabled={!input.trim()}>
            Send
          </button>
        )}
      </div>
    </div>
  );
}
