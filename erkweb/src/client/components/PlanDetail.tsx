import type {PlanRow} from '../../shared/types.js';
import './PlanDetail.css';

interface PlanDetailProps {
  plan: PlanRow;
  onClose: () => void;
}

export function PlanDetail({plan, onClose}: PlanDetailProps) {
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
      </div>
    </div>
  );
}
