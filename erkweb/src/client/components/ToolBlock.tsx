import {useEffect, useState} from 'react';

import type {ChatMessageContent} from '../../shared/types.js';
import './ToolBlock.css';

function summarizeTool(toolName: string, toolInput: Record<string, unknown>): string {
  switch (toolName) {
    case 'Bash': {
      const cmd = toolInput.command;
      if (typeof cmd === 'string') {
        return cmd.length > 60 ? cmd.slice(0, 60) + '...' : cmd;
      }
      return 'Running command...';
    }
    case 'Edit': {
      const fp = toolInput.file_path;
      return typeof fp === 'string' ? fp.split('/').slice(-2).join('/') : 'file';
    }
    case 'Write': {
      const fp = toolInput.file_path;
      return typeof fp === 'string' ? fp.split('/').slice(-2).join('/') : 'file';
    }
    case 'Read': {
      const fp = toolInput.file_path;
      return typeof fp === 'string' ? fp.split('/').slice(-2).join('/') : 'file';
    }
    case 'Glob':
      return typeof toolInput.pattern === 'string' ? toolInput.pattern : 'pattern';
    case 'Grep':
      return typeof toolInput.pattern === 'string' ? toolInput.pattern : 'search';
    case 'Task':
      return typeof toolInput.description === 'string' ? toolInput.description : 'subagent';
    default:
      return toolName;
  }
}

interface ToolBlockProps {
  toolUse: ChatMessageContent;
  toolResult?: ChatMessageContent;
}

export function ToolBlock({toolUse, toolResult}: ToolBlockProps) {
  const [expanded, setExpanded] = useState(false);

  // Auto-expand when result arrives
  useEffect(() => {
    if (toolResult) {
      setExpanded(true);
    }
  }, [toolResult]);
  const toolName = toolUse.toolName ?? 'Unknown';
  const toolInput = toolUse.toolInput ?? {};
  const summary = summarizeTool(toolName, toolInput);

  return (
    <div className={`tool-block ${toolResult?.isError ? 'tool-error' : ''}`}>
      <div className="tool-header" onClick={() => setExpanded(!expanded)}>
        <span className="tool-chevron">{expanded ? '\u25BC' : '\u25B6'}</span>
        <span className="tool-name">{toolName}</span>
        <span className="tool-summary">{summary}</span>
        {toolResult && (
          <span className={`tool-status ${toolResult.isError ? 'error' : 'success'}`}>
            {toolResult.isError ? 'failed' : 'done'}
          </span>
        )}
        {!toolResult && <span className="tool-status running">running</span>}
      </div>
      {expanded && (
        <div className="tool-details">
          <div className="tool-input">
            <div className="tool-section-label">Input</div>
            <pre>{JSON.stringify(toolInput, null, 2)}</pre>
          </div>
          {toolResult?.output && (
            <div className="tool-output">
              <div className="tool-section-label">Output{toolResult.isError ? ' (error)' : ''}</div>
              <pre>{toolResult.output}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
