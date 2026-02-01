import React, { useCallback, useEffect, useRef, useState } from "react";
import type { PlanRow } from "../types/erkdesk";
import SplitPane from "./components/SplitPane";
import PlanList from "./components/PlanList";
import ActionToolbar from "./components/ActionToolbar";

const REFRESH_INTERVAL_MS = 15_000;

const App: React.FC = () => {
  const [plans, setPlans] = useState<PlanRow[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const lastLoadedUrlRef = useRef<string | null>(null);

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

  useEffect(() => {
    const intervalId = setInterval(() => {
      window.erkdesk.fetchPlans().then((result) => {
        if (!result.success) return;
        setPlans((prevPlans) => {
          const newPlans = result.plans;
          setSelectedIndex((prevIndex) => {
            const previousIssueNumber = prevPlans[prevIndex]?.issue_number;
            if (previousIssueNumber === undefined) return 0;
            const newIndex = newPlans.findIndex(
              (p) => p.issue_number === previousIssueNumber,
            );
            return newIndex >= 0 ? newIndex : 0;
          });
          return newPlans;
        });
      });
    }, REFRESH_INTERVAL_MS);
    return () => clearInterval(intervalId);
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
    if (selectedIndex < 0 || selectedIndex >= plans.length) return;
    const plan = plans[selectedIndex];
    const url = plan.pr_url ?? plan.issue_url;
    if (url && url !== lastLoadedUrlRef.current) {
      lastLoadedUrlRef.current = url;
      window.erkdesk.loadWebViewURL(url);
    }
  }, [selectedIndex, plans]);

  const selectedPlan =
    selectedIndex >= 0 ? (plans[selectedIndex] ?? null) : null;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <ActionToolbar selectedPlan={selectedPlan} />
      <SplitPane
        leftPane={
          <PlanList
            plans={plans}
            selectedIndex={selectedIndex}
            onSelectIndex={setSelectedIndex}
            loading={loading}
            error={error}
          />
        }
      />
    </div>
  );
};

export default App;
