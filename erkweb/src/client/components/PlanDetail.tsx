import {useState} from 'react';

import type {ActionResult, PlanRow} from '../../shared/types.js';
import './PlanDetail.css';

interface PlanDetailProps {
  plan: PlanRow;
  onClose: () => void;
}

type ActionState = 'idle' | 'running' | 'success' | 'error';

interface ActionStatus {
  state: ActionState;
  message?: string;
}

async function runAction(issueNumber: number, action: string): Promise<ActionResult> {
  const res = await fetch(`/api/plans/${issueNumber}/${action}`, {method: 'POST'});
  return res.json();
}

function copyToClipboard(text: string, setToast: (msg: string) => void) {
  navigator.clipboard.writeText(text).then(
    () => setToast('Copied!'),
    () => setToast('Copy failed'),
  );
}

export function PlanDetail({plan, onClose}: PlanDetailProps) {
  const [actionStatuses, setActionStatuses] = useState<Record<string, ActionStatus>>({});
  const [toast, setToast] = useState<string | null>(null);

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 2000);
  }

  async function executeAction(actionKey: string) {
    setActionStatuses((prev) => ({...prev, [actionKey]: {state: 'running'}}));
    try {
      const result = await runAction(plan.issue_number, actionKey);
      if (result.success) {
        setActionStatuses((prev) => ({
          ...prev,
          [actionKey]: {state: 'success', message: result.output},
        }));
      } else {
        setActionStatuses((prev) => ({
          ...prev,
          [actionKey]: {state: 'error', message: result.error},
        }));
      }
    } catch (err) {
      setActionStatuses((prev) => ({
        ...prev,
        [actionKey]: {
          state: 'error',
          message: err instanceof Error ? err.message : 'Request failed',
        },
      }));
    }
  }

  const isMerged = plan.pr_state === 'merged';
  const hasPR = plan.pr_number !== null;
  const hasComments = !plan.comments_display.endsWith('/0');

  return (
    <div className="plan-detail">
      <div className="detail-header">
        <span className="detail-title">
          #{plan.issue_number} {plan.title}
        </span>
        <button className="detail-close" onClick={onClose}>
          &times;
        </button>
      </div>
      <div className="detail-content">
        {/* Issue - full width */}
        <div className="detail-section">
          <div className="detail-label">Issue</div>
          <div className="detail-value">
            {plan.issue_url ? (
              <a href={plan.issue_url} target="_blank" rel="noopener noreferrer">
                #{plan.issue_number} - {plan.full_title}
              </a>
            ) : (
              plan.full_title
            )}
          </div>
        </div>

        {/* Metadata grid */}
        <div className="detail-grid">
          <div className="detail-cell">
            <div className="detail-label">PR</div>
            <div className="detail-value">
              {plan.pr_url ? (
                <a href={plan.pr_url} target="_blank" rel="noopener noreferrer">
                  {plan.pr_display}
                </a>
              ) : (
                <span className="detail-muted">{plan.pr_display || 'None'}</span>
              )}
              {plan.pr_state && (
                <span className={`detail-badge pr-state-${plan.pr_state}`}>{plan.pr_state}</span>
              )}
            </div>
          </div>

          <div className="detail-cell">
            <div className="detail-label">Checks</div>
            <div className="detail-value">{plan.checks_display || '-'}</div>
          </div>

          <div className="detail-cell">
            <div className="detail-label">Comments</div>
            <div className="detail-value">{plan.comments_display || '-'}</div>
          </div>

          <div className="detail-cell">
            <div className="detail-label">Objective</div>
            <div className="detail-value">
              {plan.objective_display || <span className="detail-muted">None</span>}
            </div>
          </div>

          <div className="detail-cell">
            <div className="detail-label">Worktree</div>
            <div className="detail-value">
              <code>{plan.worktree_name}</code>
              {plan.exists_locally ? (
                <span className="detail-badge local">local</span>
              ) : (
                <span className="detail-badge remote">remote only</span>
              )}
            </div>
          </div>

          <div className="detail-cell">
            <div className="detail-label">Branch</div>
            <div className="detail-value">
              {plan.worktree_branch ? (
                <code>{plan.worktree_branch}</code>
              ) : (
                <span className="detail-muted">-</span>
              )}
            </div>
          </div>

          <div className="detail-cell">
            <div className="detail-label">Implementation</div>
            <div className="detail-value">
              L: {plan.local_impl_display || '-'} / R: {plan.remote_impl_display || '-'}
            </div>
          </div>

          <div className="detail-cell">
            <div className="detail-label">Run</div>
            <div className="detail-value">
              {plan.run_url ? (
                <a href={plan.run_url} target="_blank" rel="noopener noreferrer">
                  {plan.run_state_display}
                </a>
              ) : (
                plan.run_state_display || '-'
              )}
            </div>
          </div>
        </div>

        {/* Actions & Commands side by side */}
        <div className="detail-commands-actions">
          <div className="detail-actions">
            <div className="detail-label">Actions</div>
            <ActionButton
              label="Submit to Queue"
              actionKey="submit"
              status={actionStatuses['submit']}
              disabled={isMerged}
              onClick={() => executeAction('submit')}
            />
            <ActionButton
              label="Address PR Remote"
              actionKey="address-remote"
              status={actionStatuses['address-remote']}
              disabled={!hasPR || isMerged || !hasComments}
              onClick={() => executeAction('address-remote')}
            />
            <ActionButton
              label="Fix Conflicts Remote"
              actionKey="fix-conflicts"
              status={actionStatuses['fix-conflicts']}
              disabled={!hasPR || isMerged}
              onClick={() => executeAction('fix-conflicts')}
            />
            <ActionButton
              label="Land PR"
              actionKey="land"
              status={actionStatuses['land']}
              disabled={!hasPR || isMerged}
              onClick={() => executeAction('land')}
            />
            <ActionButton
              label="Close Plan"
              actionKey="close"
              status={actionStatuses['close']}
              disabled={isMerged}
              onClick={() => executeAction('close')}
            />
          </div>

          <div className="detail-copy-section">
            <div className="detail-label">Commands</div>
            <div className="detail-copy-col">
              {hasPR && <CodeSnippet code={`erk pr co ${plan.pr_number}`} onCopy={showToast} />}
              <CodeSnippet code={`erk prepare ${plan.issue_number}`} onCopy={showToast} />
              <CodeSnippet
                code={`source "$(erk prepare ${plan.issue_number} --script)" && erk implement --dangerous`}
                onCopy={showToast}
              />
              <CodeSnippet code={`erk plan submit ${plan.issue_number}`} onCopy={showToast} />
            </div>
            {toast && <div className="detail-toast">{toast}</div>}
          </div>
        </div>
      </div>
    </div>
  );
}

function ActionButton({
  label,
  status,
  disabled,
  onClick,
}: {
  label: string;
  actionKey: string;
  status?: ActionStatus;
  disabled: boolean;
  onClick: () => void;
}) {
  const isRunning = status?.state === 'running';

  return (
    <div className="action-item">
      <button
        className={`detail-action-btn ${status?.state === 'success' ? 'action-success' : ''} ${status?.state === 'error' ? 'action-error' : ''}`}
        disabled={disabled || isRunning}
        onClick={onClick}
      >
        {isRunning ? `${label}...` : label}
      </button>
      {status?.state === 'error' && status.message && (
        <div className="action-error-msg">{status.message}</div>
      )}
      {status?.state === 'success' && status.message && (
        <div className="action-success-msg">{status.message}</div>
      )}
    </div>
  );
}

function CodeSnippet({code, onCopy}: {code: string; onCopy: (msg: string) => void}) {
  return (
    <button className="detail-code-snippet" onClick={() => copyToClipboard(code, onCopy)}>
      <code>{code}</code>
    </button>
  );
}
