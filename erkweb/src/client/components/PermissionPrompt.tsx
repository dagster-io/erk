import type {PermissionRequest} from '../hooks/useChat.js';
import './PermissionPrompt.css';

function summarizePermission(toolName: string, toolInput: Record<string, unknown>): string {
  switch (toolName) {
    case 'Bash': {
      const cmd = toolInput.command;
      return typeof cmd === 'string' ? cmd : 'Run command';
    }
    case 'Edit': {
      const fp = toolInput.file_path;
      return typeof fp === 'string' ? `Edit ${fp}` : 'Edit file';
    }
    case 'Write': {
      const fp = toolInput.file_path;
      return typeof fp === 'string' ? `Write ${fp}` : 'Write file';
    }
    case 'Read': {
      const fp = toolInput.file_path;
      return typeof fp === 'string' ? `Read ${fp}` : 'Read file';
    }
    case 'Glob':
      return typeof toolInput.pattern === 'string' ? `Glob ${toolInput.pattern}` : 'Search files';
    case 'Grep':
      return typeof toolInput.pattern === 'string' ? `Grep ${toolInput.pattern}` : 'Search content';
    case 'Task':
      return typeof toolInput.description === 'string' ? toolInput.description : 'Run subagent';
    default:
      return toolName;
  }
}

interface PermissionPromptProps {
  request: PermissionRequest;
  onRespond: (toolUseId: string, allowed: boolean, applyAlways: boolean) => void;
}

export function PermissionPrompt({request, onRespond}: PermissionPromptProps) {
  const summary = summarizePermission(request.toolName, request.toolInput);

  return (
    <div className="permission-prompt">
      <div className="permission-header">
        <span className="permission-icon">?</span>
        <span className="permission-title">Permission requested</span>
      </div>
      <div className="permission-body">
        <div className="permission-tool">
          <span className="permission-tool-name">{request.toolName}</span>
          <span className="permission-tool-summary">{summary}</span>
        </div>
        {request.reason && <div className="permission-reason">{request.reason}</div>}
      </div>
      <div className="permission-actions">
        <button
          className="permission-btn deny"
          onClick={() => onRespond(request.toolUseId, false, false)}
        >
          Deny
        </button>
        <button
          className="permission-btn allow"
          onClick={() => onRespond(request.toolUseId, true, false)}
        >
          Allow
        </button>
        {request.hasSuggestions && (
          <button
            className="permission-btn always"
            onClick={() => onRespond(request.toolUseId, true, true)}
          >
            Always Allow
          </button>
        )}
      </div>
    </div>
  );
}
