import React, { useEffect, useRef } from "react";
import type { PlanRow } from "../../types/erkdesk";
import { StatusIndicator } from "./StatusIndicator";
import {
  derivePrStatus,
  deriveChecksStatus,
  deriveCommentsStatus,
} from "./statusHelpers";
import "./PlanList.css";

interface PlanListProps {
  plans: PlanRow[];
  selectedIndex: number;
  onSelectIndex: (index: number) => void;
  loading: boolean;
  error: string | null;
}

const PlanList: React.FC<PlanListProps> = ({
  plans,
  selectedIndex,
  onSelectIndex,
  loading,
  error,
}) => {
  const rowRefs = useRef<(HTMLTableRowElement | null)[]>([]);

  useEffect(() => {
    const row = rowRefs.current[selectedIndex];
    if (row) {
      row.scrollIntoView({ block: "nearest" });
    }
  }, [selectedIndex]);

  if (loading) {
    return <div className="plan-list__loading">Loading plans...</div>;
  }

  if (error) {
    return <div className="plan-list__error">Error: {error}</div>;
  }

  if (plans.length === 0) {
    return <div className="plan-list__empty">No plans found.</div>;
  }

  return (
    <div className="plan-list">
      <div className="plan-list__table-wrapper">
        <table className="plan-list__table">
          <thead>
            <tr>
              <th className="plan-list__col-number">#</th>
              <th className="plan-list__col-title">Title</th>
              <th className="plan-list__col-pr">PR</th>
              <th className="plan-list__col-checks">Chks</th>
              <th className="plan-list__col-comments">Cmts</th>
              <th className="plan-list__col-wt">WT</th>
              <th className="plan-list__col-local">Local</th>
            </tr>
          </thead>
          <tbody>
            {plans.map((plan, index) => (
              <tr
                key={plan.issue_number}
                ref={(el) => {
                  rowRefs.current[index] = el;
                }}
                className={`plan-list__row${index === selectedIndex ? " plan-list__row--selected" : ""}`}
                onClick={() => onSelectIndex(index)}
              >
                <td className="plan-list__col-number">{plan.issue_number}</td>
                <td className="plan-list__col-title">{plan.title}</td>
                <td className="plan-list__col-pr plan-list__status-cell">
                  <StatusIndicator {...derivePrStatus(plan)} />
                </td>
                <td className="plan-list__col-checks plan-list__status-cell">
                  <StatusIndicator {...deriveChecksStatus(plan)} />
                </td>
                <td className="plan-list__col-comments plan-list__status-cell">
                  <StatusIndicator {...deriveCommentsStatus(plan)} />
                </td>
                <td className="plan-list__col-wt">{plan.worktree_name}</td>
                <td className="plan-list__col-local">
                  {plan.local_impl_display}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default PlanList;
