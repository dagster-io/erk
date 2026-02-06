import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { PlanRow } from "../../types/erkdesk";
import ActionToolbar from "./ActionToolbar";

function makePlan(overrides: Partial<PlanRow> = {}): PlanRow {
  return {
    issue_number: 100,
    title: "Test Plan",
    full_title: "[erk-plan] Test Plan",
    issue_url: "https://github.com/org/repo/issues/100",
    pr_number: 42,
    pr_url: "https://github.com/org/repo/pull/42",
    pr_display: "#42",
    pr_state: "OPEN",
    checks_display: "pass",
    comments_display: "0",
    objective_display: "—",
    learn_display_icon: "",
    worktree_name: "slot-1",
    local_impl_display: "—",
    remote_impl_display: "—",
    run_state_display: "—",
    exists_locally: true,
    run_url: "https://github.com/org/repo/actions/runs/123",
    worktree_branch: "feature-branch",
    pr_head_branch: "feature-branch",
    ...overrides,
  };
}

describe("ActionToolbar", () => {
  const mockOnActionStart = vi.fn();
  const mockOnSummonTerminal = vi.fn();

  beforeEach(() => {
    mockOnActionStart.mockReset();
    mockOnSummonTerminal.mockReset();
  });

  it("renders all six buttons", () => {
    render(
      <ActionToolbar
        selectedPlan={makePlan()}
        runningActionId={null}
        onActionStart={mockOnActionStart}
        onSummonTerminal={mockOnSummonTerminal}
      />,
    );
    expect(screen.getByText("Submit")).toBeInTheDocument();
    expect(screen.getByText("Land")).toBeInTheDocument();
    expect(screen.getByText("Address")).toBeInTheDocument();
    expect(screen.getByText("Fix Conflicts")).toBeInTheDocument();
    expect(screen.getByText("Close")).toBeInTheDocument();
    expect(screen.getByText("Terminal")).toBeInTheDocument();
  });

  it("all buttons enabled when plan has PR, run_url, and OPEN state", () => {
    render(
      <ActionToolbar
        selectedPlan={makePlan()}
        runningActionId={null}
        onActionStart={mockOnActionStart}
        onSummonTerminal={mockOnSummonTerminal}
      />,
    );
    const buttons = screen.getAllByRole("button");
    for (const button of buttons) {
      expect(button).not.toBeDisabled();
    }
  });

  it("all buttons disabled when no plan selected", () => {
    render(
      <ActionToolbar
        selectedPlan={null}
        runningActionId={null}
        onActionStart={mockOnActionStart}
        onSummonTerminal={mockOnSummonTerminal}
      />,
    );
    const buttons = screen.getAllByRole("button");
    for (const button of buttons) {
      expect(button).toBeDisabled();
    }
  });

  it("disables Land when pr_state is not OPEN", () => {
    render(
      <ActionToolbar
        selectedPlan={makePlan({ pr_state: "MERGED" })}
        runningActionId={null}
        onActionStart={mockOnActionStart}
        onSummonTerminal={mockOnSummonTerminal}
      />,
    );
    expect(screen.getByText("Land")).toBeDisabled();
    expect(screen.getByText("Submit")).not.toBeDisabled();
  });

  it("disables Land when run_url is null", () => {
    render(
      <ActionToolbar
        selectedPlan={makePlan({ run_url: null })}
        runningActionId={null}
        onActionStart={mockOnActionStart}
        onSummonTerminal={mockOnSummonTerminal}
      />,
    );
    expect(screen.getByText("Land")).toBeDisabled();
  });

  it("disables Address and Fix Conflicts when no PR", () => {
    render(
      <ActionToolbar
        selectedPlan={makePlan({ pr_number: null })}
        runningActionId={null}
        onActionStart={mockOnActionStart}
        onSummonTerminal={mockOnSummonTerminal}
      />,
    );
    expect(screen.getByText("Address")).toBeDisabled();
    expect(screen.getByText("Fix Conflicts")).toBeDisabled();
  });

  it("disables Submit when no issue_url", () => {
    render(
      <ActionToolbar
        selectedPlan={makePlan({ issue_url: null })}
        runningActionId={null}
        onActionStart={mockOnActionStart}
        onSummonTerminal={mockOnSummonTerminal}
      />,
    );
    expect(screen.getByText("Submit")).toBeDisabled();
  });

  it("Close is always enabled when plan selected", () => {
    render(
      <ActionToolbar
        selectedPlan={makePlan({ pr_number: null, issue_url: null })}
        runningActionId={null}
        onActionStart={mockOnActionStart}
        onSummonTerminal={mockOnSummonTerminal}
      />,
    );
    expect(screen.getByText("Close")).not.toBeDisabled();
  });

  it("calls onActionStart with correct command for Submit", async () => {
    render(
      <ActionToolbar
        selectedPlan={makePlan()}
        runningActionId={null}
        onActionStart={mockOnActionStart}
        onSummonTerminal={mockOnSummonTerminal}
      />,
    );
    const user = userEvent.setup();
    await user.click(screen.getByText("Submit"));

    expect(mockOnActionStart).toHaveBeenCalledWith("submit_to_queue", "erk", [
      "plan",
      "submit",
      "100",
    ]);
  });

  it("calls onActionStart with correct command for Land", async () => {
    render(
      <ActionToolbar
        selectedPlan={makePlan()}
        runningActionId={null}
        onActionStart={mockOnActionStart}
        onSummonTerminal={mockOnSummonTerminal}
      />,
    );
    const user = userEvent.setup();
    await user.click(screen.getByText("Land"));

    expect(mockOnActionStart).toHaveBeenCalledWith("land_pr", "erk", [
      "exec",
      "land-execute",
      "--pr-number=42",
      "--branch=feature-branch",
      "-f",
    ]);
  });

  it("calls onActionStart with correct command for Close", async () => {
    render(
      <ActionToolbar
        selectedPlan={makePlan()}
        runningActionId={null}
        onActionStart={mockOnActionStart}
        onSummonTerminal={mockOnSummonTerminal}
      />,
    );
    const user = userEvent.setup();
    await user.click(screen.getByText("Close"));

    expect(mockOnActionStart).toHaveBeenCalledWith("close_plan", "erk", [
      "exec",
      "close-plan",
      "100",
    ]);
  });

  it("calls onActionStart with correct command for Address", async () => {
    render(
      <ActionToolbar
        selectedPlan={makePlan()}
        runningActionId={null}
        onActionStart={mockOnActionStart}
        onSummonTerminal={mockOnSummonTerminal}
      />,
    );
    const user = userEvent.setup();
    await user.click(screen.getByText("Address"));

    expect(mockOnActionStart).toHaveBeenCalledWith("address_remote", "erk", [
      "launch",
      "pr-address",
      "--pr",
      "42",
    ]);
  });

  it("calls onActionStart with correct command for Fix Conflicts", async () => {
    render(
      <ActionToolbar
        selectedPlan={makePlan()}
        runningActionId={null}
        onActionStart={mockOnActionStart}
        onSummonTerminal={mockOnSummonTerminal}
      />,
    );
    const user = userEvent.setup();
    await user.click(screen.getByText("Fix Conflicts"));

    expect(mockOnActionStart).toHaveBeenCalledWith(
      "fix_conflicts_remote",
      "erk",
      ["launch", "pr-fix-conflicts", "--pr", "42"],
    );
  });

  it("disables all buttons while action is running", () => {
    render(
      <ActionToolbar
        selectedPlan={makePlan()}
        runningActionId="submit_to_queue"
        onActionStart={mockOnActionStart}
        onSummonTerminal={mockOnSummonTerminal}
      />,
    );

    expect(screen.getByText("Submit...")).toBeInTheDocument();
    const buttons = screen.getAllByRole("button");
    for (const button of buttons) {
      expect(button).toBeDisabled();
    }
  });

  it("shows running state for the correct button", () => {
    render(
      <ActionToolbar
        selectedPlan={makePlan()}
        runningActionId="land_pr"
        onActionStart={mockOnActionStart}
        onSummonTerminal={mockOnSummonTerminal}
      />,
    );

    expect(screen.getByText("Land...")).toBeInTheDocument();
    expect(screen.getByText("Submit")).toBeInTheDocument();
  });

  it("calls onSummonTerminal with plan issue_number when Terminal clicked", async () => {
    render(
      <ActionToolbar
        selectedPlan={makePlan()}
        runningActionId={null}
        onActionStart={mockOnActionStart}
        onSummonTerminal={mockOnSummonTerminal}
      />,
    );
    const user = userEvent.setup();
    await user.click(screen.getByText("Terminal"));

    expect(mockOnSummonTerminal).toHaveBeenCalledWith(100);
  });

  it("disables Terminal when exists_locally is false", () => {
    render(
      <ActionToolbar
        selectedPlan={makePlan({ exists_locally: false })}
        runningActionId={null}
        onActionStart={mockOnActionStart}
        onSummonTerminal={mockOnSummonTerminal}
      />,
    );
    expect(screen.getByText("Terminal")).toBeDisabled();
  });
});
