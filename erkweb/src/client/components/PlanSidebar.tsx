import type {PlanRow} from '../../shared/types.js';
import './PlanSidebar.css';

interface PlanSidebarProps {
  plans: PlanRow[];
  loading: boolean;
  error: string | null;
  selectedPlan: PlanRow | null;
  onSelect: (plan: PlanRow) => void;
}

export function PlanSidebar({plans, loading, error, selectedPlan, onSelect}: PlanSidebarProps) {
  return (
    <div className="plan-sidebar">
      <div className="sidebar-header">
        <span className="sidebar-title">Plans</span>
        <span className="sidebar-count">{plans.length}</span>
      </div>
      <div className="sidebar-content">
        {loading && <div className="sidebar-status">Loading...</div>}
        {error && <div className="sidebar-error">{error}</div>}
        {!loading && !error && plans.length === 0 && (
          <div className="sidebar-status">No plans found</div>
        )}
        {plans.map((plan) => (
          <div
            key={plan.issue_number}
            className={`plan-item ${selectedPlan?.issue_number === plan.issue_number ? 'selected' : ''}`}
            onClick={() => onSelect(plan)}
          >
            <div className="plan-primary">
              <span className="plan-number">#{plan.issue_number}</span>
              <span className="plan-title">{plan.title}</span>
            </div>
            <div className="plan-meta">
              <span className="plan-meta-tag">
                impl: <span className="plan-meta-value">{plan.local_impl_display || 'none'}</span>
              </span>
              <span className="plan-meta-tag">
                pr: <span className="plan-meta-value">{plan.pr_display || 'none'}</span>
              </span>
              <span className="plan-meta-tag">
                checks: <span className="plan-meta-value">{plan.checks_display || 'none'}</span>
              </span>
              <span className="plan-meta-tag">
                run: <span className="plan-meta-value">{plan.run_state_display || 'none'}</span>
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
