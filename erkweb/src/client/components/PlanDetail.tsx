import {useEffect, useState} from 'react';

import type {PlanRow} from '../../shared/types.js';
import './PlanDetail.css';

interface ImplStatus {
  hasImpl: boolean;
  implValid: boolean;
  worktreePath?: string;
}

interface PlanDetailProps {
  plan: PlanRow;
  onClose: () => void;
  onSend: (text: string, options?: {cwd?: string; newSession?: boolean}) => void;
  isStreaming: boolean;
}

export function PlanDetail({plan, onClose, onSend, isStreaming}: PlanDetailProps) {
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [implStatus, setImplStatus] = useState<ImplStatus | null>(null);

  // Fetch impl status when the selected plan changes
  useEffect(() => {
    setImplStatus(null);
    if (!plan.exists_locally) {
      return;
    }

    let cancelled = false;
    fetch(`/api/plans/${plan.issue_number}/impl-status`)
      .then((res) => res.json())
      .then((data) => {
        if (!cancelled && data.success) {
          setImplStatus({
            hasImpl: data.hasImpl,
            implValid: data.implValid,
            worktreePath: data.worktreePath,
          });
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [plan.issue_number, plan.exists_locally]);

  async function resolveWorktreePath(): Promise<string | null> {
    // Use cached worktree path from impl-status if available
    if (implStatus?.worktreePath) {
      return implStatus.worktreePath;
    }

    const res = await fetch(`/api/plans/${plan.issue_number}/worktree-path`);
    const data = await res.json();
    if (!data.success) {
      setActionError(data.error ?? 'Failed to resolve worktree path');
      return null;
    }
    return data.worktreePath;
  }

  async function handleImplement() {
    setBusy(true);
    setActionError(null);
    try {
      const res = await fetch(`/api/plans/${plan.issue_number}/prepare`, {method: 'POST'});
      const data = await res.json();
      if (!data.success) {
        setActionError(data.error ?? 'Failed to prepare worktree');
        return;
      }
      onSend(`/erk:plan-implement ${plan.issue_number}`, {
        cwd: data.worktreePath,
        newSession: true,
      });
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Prepare request failed');
    } finally {
      setBusy(false);
    }
  }

  async function handleAddressFeedback() {
    setBusy(true);
    setActionError(null);
    try {
      const cwd = await resolveWorktreePath();
      if (cwd) {
        onSend('/erk:pr-address', {cwd, newSession: true});
      }
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Request failed');
    } finally {
      setBusy(false);
    }
  }

  async function handleContinueImpl() {
    setBusy(true);
    setActionError(null);
    try {
      const cwd = await resolveWorktreePath();
      if (cwd) {
        onSend(
          'Read .impl/progress.md and .impl/plan.md, then continue the implementation from where it left off.',
          {cwd, newSession: true},
        );
      }
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Request failed');
    } finally {
      setBusy(false);
    }
  }

  const isMerged = plan.pr_state === 'merged';
  const hasLocalWorktree = plan.exists_locally;
  const hasPR = plan.pr_number !== null;
  const hasActiveImpl = implStatus?.implValid === true;
  const hasComments = !plan.comments_display.endsWith('/0');
  const canImplement = !isMerged && !hasPR;
  const canAddressFeedback = hasPR && hasLocalWorktree && !isMerged && hasComments;
  const canContinueImpl = hasActiveImpl && !isMerged && !hasPR;

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

        <div className="detail-section">
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

        <div className="detail-section">
          <div className="detail-label">Checks</div>
          <div className="detail-value">{plan.checks_display || '-'}</div>
        </div>

        <div className="detail-section">
          <div className="detail-label">Comments</div>
          <div className="detail-value">{plan.comments_display || '-'}</div>
        </div>

        <div className="detail-section">
          <div className="detail-label">Objective</div>
          <div className="detail-value">
            {plan.objective_display || <span className="detail-muted">None</span>}
          </div>
        </div>

        <div className="detail-section">
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

        {plan.worktree_branch && (
          <div className="detail-section">
            <div className="detail-label">Branch</div>
            <div className="detail-value">
              <code>{plan.worktree_branch}</code>
            </div>
          </div>
        )}

        <div className="detail-section">
          <div className="detail-label">Implementation</div>
          <div className="detail-value">
            Local: {plan.local_impl_display || '-'} / Remote: {plan.remote_impl_display || '-'}
          </div>
        </div>

        <div className="detail-actions">
          <button
            className="detail-action-btn implement-btn"
            disabled={isStreaming || busy || !canImplement}
            onClick={handleImplement}
          >
            {busy ? 'Preparing...' : 'Implement'}
          </button>
          <button
            className="detail-action-btn feedback-btn"
            disabled={isStreaming || busy || !canAddressFeedback}
            onClick={handleAddressFeedback}
          >
            Address PR Feedback
          </button>
          <button
            className="detail-action-btn continue-btn"
            disabled={isStreaming || busy || !canContinueImpl}
            onClick={handleContinueImpl}
          >
            Continue Implementation
          </button>
          {actionError && <div className="detail-action-error">{actionError}</div>}
        </div>
      </div>
    </div>
  );
}
