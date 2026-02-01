import React, { useCallback, useEffect, useRef, useState } from "react";
import type {
  PlanRow,
  ActionOutputEvent,
  ActionCompletedEvent,
  ContextMenuAction,
} from "../types/erkdesk";
import SplitPane from "./components/SplitPane";
import PlanList from "./components/PlanList";
import ActionToolbar, { ACTIONS } from "./components/ActionToolbar";
import { LogPanel, LogLine } from "./components/LogPanel";

const REFRESH_INTERVAL_MS = 15_000;

const App: React.FC = () => {
  const [plans, setPlans] = useState<PlanRow[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [runningAction, setRunningAction] = useState<string | null>(null);
  const lastLoadedUrlRef = useRef<string | null>(null);

  const [logLines, setLogLines] = useState<LogLine[]>([]);
  const [logStatus, setLogStatus] = useState<"running" | "success" | "error">(
    "running",
  );
  const [logVisible, setLogVisible] = useState(false);
  const [runningActionId, setRunningActionId] = useState<string | null>(null);

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

  const handleActionStart = useCallback(
    (actionId: string, command: string, args: string[]) => {
      setLogLines([]);
      setLogStatus("running");
      setLogVisible(true);
      setRunningActionId(actionId);
      window.erkdesk.startStreamingAction(command, args);
    },
    [],
  );

  const handleLogDismiss = useCallback(() => {
    setLogVisible(false);
  }, []);

  useEffect(() => {
    const onOutput = (event: ActionOutputEvent) => {
      setLogLines((prev) => [
        ...prev,
        { stream: event.stream, text: event.data },
      ]);
    };

    const onCompleted = (event: ActionCompletedEvent) => {
      setLogStatus(event.success ? "success" : "error");
      setRunningActionId(null);
    };

    window.erkdesk.onActionOutput(onOutput);
    window.erkdesk.onActionCompleted(onCompleted);

    return () => {
      window.erkdesk.removeActionListeners();
    };
  }, []);

  const selectedPlan =
    selectedIndex >= 0 ? (plans[selectedIndex] ?? null) : null;

  const handleExecuteAction = useCallback(async (actionId: string, plan: PlanRow) => {
    if (runningAction !== null) return;

    const action = ACTIONS.find((a) => a.id === actionId);
    if (!action) return;

    setRunningAction(actionId);
    const { command, args } = action.getCommand(plan);
    try {
      await window.erkdesk.executeAction(command, args);
    } finally {
      setRunningAction(null);
    }
  }, [runningAction]);

  const handleContextMenu = useCallback((plan: PlanRow) => {
    window.erkdesk.showContextMenu(plan);
  }, []);

  useEffect(() => {
    const cleanup = window.erkdesk.onContextMenuAction((action: ContextMenuAction) => {
      if (action.type === "open_url") {
        window.erkdesk.loadWebViewURL(action.payload);
      } else if (action.type === "copy") {
        navigator.clipboard.writeText(action.payload);
      } else if (action.type === "execute") {
        if (selectedPlan) {
          handleExecuteAction(action.payload, selectedPlan);
        }
      }
    });
    return cleanup;
  }, [handleExecuteAction, selectedPlan]);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <ActionToolbar
        selectedPlan={selectedPlan}
        runningActionId={runningActionId}
        onActionStart={handleActionStart}
      />
      <SplitPane
        leftPane={
          <PlanList
            plans={plans}
            selectedIndex={selectedIndex}
            onSelectIndex={setSelectedIndex}
            onContextMenu={handleContextMenu}
            loading={loading}
            error={error}
          />
        }
      />
      {logVisible && (
        <LogPanel
          lines={logLines}
          status={logStatus}
          onDismiss={handleLogDismiss}
        />
      )}
    </div>
  );
};

export default App;
