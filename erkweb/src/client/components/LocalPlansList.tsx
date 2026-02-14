import type {LocalPlanFile} from '../../shared/types.js';
import './LocalPlansList.css';

interface LocalPlansListProps {
  plans: LocalPlanFile[];
  loading: boolean;
  error: string | null;
  selectedSlug: string | null;
  onSelect: (slug: string) => void;
}

function formatRelativeTime(ms: number): string {
  const seconds = Math.floor((Date.now() - ms) / 1000);
  if (seconds < 60) {
    return 'just now';
  }
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `${minutes}m ago`;
  }
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `${hours}h ago`;
  }
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function LocalPlansList({
  plans,
  loading,
  error,
  selectedSlug,
  onSelect,
}: LocalPlansListProps) {
  return (
    <div className="local-plans-list">
      <div className="sidebar-header">
        <span className="sidebar-title">Local Plans</span>
        <span className="sidebar-count">{plans.length}</span>
      </div>
      <div className="sidebar-content">
        {loading && <div className="sidebar-status">Loading...</div>}
        {error && <div className="sidebar-error">{error}</div>}
        {!loading && !error && plans.length === 0 && (
          <div className="sidebar-status">No local plans found</div>
        )}
        {plans.map((plan) => (
          <div
            key={plan.slug}
            className={`plan-item ${selectedSlug === plan.slug ? 'selected' : ''}`}
            onClick={() => onSelect(plan.slug)}
          >
            <div className="plan-primary">
              <span className="plan-title">{plan.title}</span>
            </div>
            <div className="local-plan-meta">
              {plan.commentCount > 0 ? (
                <span className="local-plan-comments">
                  {plan.commentCount} comment{plan.commentCount !== 1 ? 's' : ''}
                </span>
              ) : (
                <span className="local-plan-no-comments">No comments</span>
              )}
              <span className="local-plan-time">{formatRelativeTime(plan.modifiedAt)}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
