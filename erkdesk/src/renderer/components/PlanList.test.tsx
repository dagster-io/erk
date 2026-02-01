import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { PlanRow } from "../../types/erkdesk";
import PlanList from "./PlanList";

function makePlan(overrides: Partial<PlanRow> = {}): PlanRow {
  return {
    issue_number: 1,
    title: "Test Plan",
    full_title: "[erk-plan] Test Plan",
    issue_url: "https://github.com/org/repo/issues/1",
    pr_number: null,
    pr_url: null,
    pr_display: "—",
    pr_state: null,
    checks_display: "—",
    comments_display: "—",
    objective_display: "—",
    learn_display_icon: "",
    worktree_name: "slot-1",
    local_impl_display: "—",
    remote_impl_display: "—",
    run_state_display: "—",
    exists_locally: false,
    ...overrides,
  };
}

describe("PlanList", () => {
  beforeEach(() => {
    // Reset the mock before each test
    vi.mocked(window.erkdesk.fetchPlans).mockReset();
  });

  it("renders loading state initially", () => {
    // Keep the promise pending so loading state persists
    vi.mocked(window.erkdesk.fetchPlans).mockReturnValue(new Promise(() => {}));
    render(<PlanList />);
    expect(screen.getByText("Loading plans...")).toBeInTheDocument();
  });

  it("renders plan rows after successful fetch", async () => {
    const plans = [
      makePlan({ issue_number: 10, title: "Alpha" }),
      makePlan({ issue_number: 20, title: "Beta" }),
    ];
    vi.mocked(window.erkdesk.fetchPlans).mockResolvedValue({
      success: true,
      plans,
      count: 2,
    });

    render(<PlanList />);

    await waitFor(() => {
      expect(screen.getByText("Alpha")).toBeInTheDocument();
    });
    expect(screen.getByText("Beta")).toBeInTheDocument();
    expect(screen.getByText("10")).toBeInTheDocument();
    expect(screen.getByText("20")).toBeInTheDocument();
  });

  it("renders error message on fetch failure", async () => {
    vi.mocked(window.erkdesk.fetchPlans).mockResolvedValue({
      success: false,
      plans: [],
      count: 0,
      error: "Network timeout",
    });

    render(<PlanList />);

    await waitFor(() => {
      expect(screen.getByText("Error: Network timeout")).toBeInTheDocument();
    });
  });

  it("renders empty state when no plans", async () => {
    vi.mocked(window.erkdesk.fetchPlans).mockResolvedValue({
      success: true,
      plans: [],
      count: 0,
    });

    render(<PlanList />);

    await waitFor(() => {
      expect(screen.getByText("No plans found.")).toBeInTheDocument();
    });
  });

  it("j/k keyboard navigation changes selected row", async () => {
    const plans = [
      makePlan({ issue_number: 1, title: "First" }),
      makePlan({ issue_number: 2, title: "Second" }),
      makePlan({ issue_number: 3, title: "Third" }),
    ];
    vi.mocked(window.erkdesk.fetchPlans).mockResolvedValue({
      success: true,
      plans,
      count: 3,
    });

    render(<PlanList />);

    await waitFor(() => {
      expect(screen.getByText("First")).toBeInTheDocument();
    });

    // First row selected by default
    const rows = screen.getAllByRole("row").slice(1); // skip header
    expect(rows[0]).toHaveClass("plan-list__row--selected");

    // Press j to move down
    const user = userEvent.setup();
    await user.keyboard("j");
    expect(rows[1]).toHaveClass("plan-list__row--selected");
    expect(rows[0]).not.toHaveClass("plan-list__row--selected");

    // Press k to move back up
    await user.keyboard("k");
    expect(rows[0]).toHaveClass("plan-list__row--selected");
    expect(rows[1]).not.toHaveClass("plan-list__row--selected");
  });

  it("ArrowDown/ArrowUp navigation works", async () => {
    const plans = [
      makePlan({ issue_number: 1, title: "First" }),
      makePlan({ issue_number: 2, title: "Second" }),
    ];
    vi.mocked(window.erkdesk.fetchPlans).mockResolvedValue({
      success: true,
      plans,
      count: 2,
    });

    render(<PlanList />);

    await waitFor(() => {
      expect(screen.getByText("First")).toBeInTheDocument();
    });

    const rows = screen.getAllByRole("row").slice(1);

    const user = userEvent.setup();
    await user.keyboard("{ArrowDown}");
    expect(rows[1]).toHaveClass("plan-list__row--selected");

    await user.keyboard("{ArrowUp}");
    expect(rows[0]).toHaveClass("plan-list__row--selected");
  });

  it("click on row selects it", async () => {
    const plans = [
      makePlan({ issue_number: 1, title: "First" }),
      makePlan({ issue_number: 2, title: "Second" }),
    ];
    vi.mocked(window.erkdesk.fetchPlans).mockResolvedValue({
      success: true,
      plans,
      count: 2,
    });

    render(<PlanList />);

    await waitFor(() => {
      expect(screen.getByText("First")).toBeInTheDocument();
    });

    const rows = screen.getAllByRole("row").slice(1);
    const user = userEvent.setup();
    await user.click(rows[1]);

    expect(rows[1]).toHaveClass("plan-list__row--selected");
    expect(rows[0]).not.toHaveClass("plan-list__row--selected");
  });

  it("selected row has plan-list__row--selected class", async () => {
    const plans = [makePlan({ issue_number: 1, title: "Only Plan" })];
    vi.mocked(window.erkdesk.fetchPlans).mockResolvedValue({
      success: true,
      plans,
      count: 1,
    });

    render(<PlanList />);

    await waitFor(() => {
      expect(screen.getByText("Only Plan")).toBeInTheDocument();
    });

    const rows = screen.getAllByRole("row").slice(1);
    expect(rows[0]).toHaveClass("plan-list__row--selected");
    expect(rows[0].className).toContain("plan-list__row--selected");
  });
});
