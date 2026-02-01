import React, { useCallback } from "react";
import type { PlanRow } from "../../types/erkdesk";
import "./ActionToolbar.css";

interface ActionToolbarProps {
  selectedPlan: PlanRow | null;
  runningActionId: string | null;
  onActionStart: (actionId: string, command: string, args: string[]) => void;
}

interface ActionDef {
  id: string;
  label: string;
  isAvailable: (plan: PlanRow) => boolean;
  getCommand: (plan: PlanRow) => { command: string; args: string[] };
}

const ACTIONS: ActionDef[] = [
  {
    id: "submit_to_queue",
    label: "Submit",
    isAvailable: (plan) => plan.issue_url !== null,
    getCommand: (plan) => ({
      command: "erk",
      args: ["plan", "submit", String(plan.issue_number)],
    }),
  },
  {
    id: "land_pr",
    label: "Land",
    isAvailable: (plan) =>
      plan.pr_number !== null &&
      plan.pr_state === "OPEN" &&
      plan.run_url !== null,
    getCommand: (plan) => ({
      command: "erk",
      args: [
        "exec",
        "land-execute",
        `--pr-number=${plan.pr_number}`,
        `--branch=${plan.pr_head_branch}`,
        "-f",
      ],
    }),
  },
  {
    id: "address_remote",
    label: "Address",
    isAvailable: (plan) => plan.pr_number !== null,
    getCommand: (plan) => ({
      command: "erk",
      args: ["launch", "pr-address", "--pr", String(plan.pr_number)],
    }),
  },
  {
    id: "fix_conflicts_remote",
    label: "Fix Conflicts",
    isAvailable: (plan) => plan.pr_number !== null,
    getCommand: (plan) => ({
      command: "erk",
      args: ["launch", "pr-fix-conflicts", "--pr", String(plan.pr_number)],
    }),
  },
  {
    id: "close_plan",
    label: "Close",
    isAvailable: () => true,
    getCommand: (plan) => ({
      command: "erk",
      args: ["exec", "close-plan", String(plan.issue_number)],
    }),
  },
];

const ActionToolbar: React.FC<ActionToolbarProps> = ({
  selectedPlan,
  runningActionId,
  onActionStart,
}) => {
  const handleClick = useCallback(
    (action: ActionDef) => {
      if (runningActionId !== null || selectedPlan === null) return;

      const { command, args } = action.getCommand(selectedPlan);
      onActionStart(action.id, command, args);
    },
    [runningActionId, selectedPlan, onActionStart],
  );

  return (
    <div className="action-toolbar">
      {ACTIONS.map((action) => {
        const available =
          selectedPlan !== null && action.isAvailable(selectedPlan);
        const disabled = !available || runningActionId !== null;
        const isRunning = runningActionId === action.id;

        return (
          <button
            key={action.id}
            className={`action-toolbar__button${isRunning ? " action-toolbar__button--running" : ""}`}
            disabled={disabled}
            onClick={() => handleClick(action)}
          >
            {isRunning ? `${action.label}...` : action.label}
          </button>
        );
      })}
    </div>
  );
};

export default ActionToolbar;
