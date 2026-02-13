import {type KeyboardEvent, useEffect, useMemo, useRef, useState} from 'react';

import {CommandTypeahead, filterCommands} from './CommandTypeahead.js';
import type {SlashCommandInfo} from '../../shared/types.js';
import './ChatPanel.css';

interface ChatInputProps {
  isStreaming: boolean;
  commands: SlashCommandInfo[];
  onSend: (text: string) => void;
  onStop: () => void;
}

export function ChatInput({isStreaming, commands, onSend, onStop}: ChatInputProps) {
  const [input, setInput] = useState('');
  const [typeaheadIndex, setTypeaheadIndex] = useState(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const slashMatch = /^\/(\S*)$/.exec(input);
  const showTypeahead = slashMatch !== null && commands.length > 0 && !isStreaming;
  const typeaheadFilter = slashMatch ? slashMatch[1] : '';
  const filteredCommands = useMemo(
    () => (showTypeahead ? filterCommands(commands, typeaheadFilter) : []),
    [commands, typeaheadFilter, showTypeahead],
  );

  useEffect(() => {
    setTypeaheadIndex(0);
  }, [typeaheadFilter]);

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
  );
}
