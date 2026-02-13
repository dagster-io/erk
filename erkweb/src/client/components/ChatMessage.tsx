import {memo} from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import {ToolBlock} from './ToolBlock.js';
import type {ChatMessage as ChatMessageType} from '../../shared/types.js';
import './ChatMessage.css';

interface ChatMessageProps {
  message: ChatMessageType;
}

export const ChatMessage = memo(function ChatMessage({message}: ChatMessageProps) {
  // Build a map of tool results by toolUseId
  const toolResults = new Map<string, (typeof message.content)[number]>();
  for (const block of message.content) {
    if (block.type === 'tool_result' && block.toolUseId) {
      toolResults.set(block.toolUseId, block);
    }
  }

  return (
    <div className={`chat-message ${message.role}`}>
      <div className="message-role">{message.role === 'user' ? 'You' : 'Claude'}</div>
      <div className="message-content">
        {message.content.map((block, i) => {
          if (block.type === 'text' && block.text) {
            return (
              <div key={i} className="text-block">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{block.text}</ReactMarkdown>
              </div>
            );
          }
          if (block.type === 'tool_use') {
            const result = block.toolUseId ? toolResults.get(block.toolUseId) : undefined;
            return <ToolBlock key={i} toolUse={block} toolResult={result} />;
          }
          // tool_result blocks are rendered inline with their tool_use
          return null;
        })}
      </div>
    </div>
  );
});
