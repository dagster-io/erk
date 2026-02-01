import React, { useCallback, useEffect, useRef, useState } from "react";
import type { PlanRow } from "../../types/erkdesk";
import "./PlanList.css";

const PlanList: React.FC = () => {
  const [plans, setPlans] = useState<PlanRow[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const rowRefs = useRef<(HTMLTableRowElement | null)[]>([]);

  useEffect(() => {
    window.erkdesk.fetchPlans().then((result) => {
      if (result.success) {
        setPlans(result.plans);
        if (result.plans.length > 0) {
          setSelectedIndex(0);
        }
      } else {
        setError(result.error ?? "Failed to fetch plans");
      }
      setLoading(false);
    });
  }, []);

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (plans.length === 0) return;

      if (event.key === "j" || event.key === "ArrowDown") {
        event.preventDefault();
        setSelectedIndex((prev) => Math.min(prev + 1, plans.length - 1));
      } else if (event.key === "k" || event.key === "ArrowUp") {
        event.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
      }
    },
    [plans.length],
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

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
                onClick={() => setSelectedIndex(index)}
              >
                <td className="plan-list__col-number">{plan.issue_number}</td>
                <td className="plan-list__col-title">{plan.title}</td>
                <td className="plan-list__col-pr">{plan.pr_display}</td>
                <td className="plan-list__col-checks">{plan.checks_display}</td>
                <td className="plan-list__col-comments">
                  {plan.comments_display}
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
