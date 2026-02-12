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
        <table className="plan-table">
          <tbody>
            {plans.map((plan) => (
              <tr
                key={plan.issue_number}
                className={`plan-row ${
                  selectedPlan?.issue_number === plan.issue_number ? 'selected' : ''
                }`}
                onClick={() => onSelect(plan)}
              >
                <td className="plan-number">#{plan.issue_number}</td>
                <td className="plan-title">{plan.title}</td>
                <td className="plan-pr">{plan.pr_display}</td>
                <td className="plan-checks">{plan.checks_display}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
