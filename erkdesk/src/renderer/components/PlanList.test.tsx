import { render, screen } from "@testing-library/react";
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
    pr_display: "\u2014",
    pr_state: null,
    checks_display: "\u2014",
    comments_display: "\u2014",
    objective_display: "\u2014",
    learn_display_icon: "",
    worktree_name: "slot-1",
    local_impl_display: "\u2014",
    remote_impl_display: "\u2014",
    run_state_display: "\u2014",
    exists_locally: false,
    run_url: null,
    worktree_branch: null,
    pr_head_branch: null,
    ...overrides,
  };
}

describe("PlanList", () => {
  const mockContextMenu = vi.fn();

  beforeEach(() => {
    mockContextMenu.mockReset();
  });

  it("renders loading state", () => {
    render(
      <PlanList
        plans={[]}
        selectedIndex={-1}
        onSelectIndex={vi.fn()}
        onContextMenu={mockContextMenu}
        loading={true}
        error={null}
      />,
    );
    expect(screen.getByText("Loading plans...")).toBeInTheDocument();
  });

  it("renders error message", () => {
    render(
      <PlanList
        plans={[]}
        selectedIndex={-1}
        onSelectIndex={vi.fn()}
        onContextMenu={mockContextMenu}
        loading={false}
        error="Network timeout"
      />,
    );
    expect(screen.getByText("Error: Network timeout")).toBeInTheDocument();
  });

  it("renders empty state when no plans", () => {
    render(
      <PlanList
        plans={[]}
        selectedIndex={-1}
        onSelectIndex={vi.fn()}
        onContextMenu={mockContextMenu}
        loading={false}
        error={null}
      />,
    );
    expect(screen.getByText("No plans found.")).toBeInTheDocument();
  });

  it("renders plan rows", () => {
    const plans = [
      makePlan({ issue_number: 10, title: "Alpha" }),
      makePlan({ issue_number: 20, title: "Beta" }),
    ];
    render(
      <PlanList
        plans={plans}
        selectedIndex={0}
        onSelectIndex={vi.fn()}
        onContextMenu={mockContextMenu}
        loading={false}
        error={null}
      />,
    );

    expect(screen.getByText("Alpha")).toBeInTheDocument();
    expect(screen.getByText("Beta")).toBeInTheDocument();
    expect(screen.getByText("10")).toBeInTheDocument();
    expect(screen.getByText("20")).toBeInTheDocument();
  });

  it("applies selected class to selected row", () => {
    const plans = [
      makePlan({ issue_number: 1, title: "First" }),
      makePlan({ issue_number: 2, title: "Second" }),
    ];
    render(
      <PlanList
        plans={plans}
        selectedIndex={1}
        onSelectIndex={vi.fn()}
        onContextMenu={mockContextMenu}
        loading={false}
        error={null}
      />,
    );

    const rows = screen.getAllByRole("row").slice(1);
    expect(rows[0]).not.toHaveClass("plan-list__row--selected");
    expect(rows[1]).toHaveClass("plan-list__row--selected");
  });

  it("calls onSelectIndex when row is clicked", async () => {
    const onSelectIndex = vi.fn();
    const plans = [
      makePlan({ issue_number: 1, title: "First" }),
      makePlan({ issue_number: 2, title: "Second" }),
    ];
    render(
      <PlanList
        plans={plans}
        selectedIndex={0}
        onSelectIndex={onSelectIndex}
        onContextMenu={mockContextMenu}
        loading={false}
        error={null}
      />,
    );

    const rows = screen.getAllByRole("row").slice(1);
    const user = userEvent.setup();
    await user.click(rows[1]);

    expect(onSelectIndex).toHaveBeenCalledWith(1);
  });

  it("calls onContextMenu when row is right-clicked", async () => {
    const plan = makePlan({ issue_number: 1, title: "First" });
    render(
      <PlanList
        plans={[plan]}
        selectedIndex={0}
        onSelectIndex={vi.fn()}
        onContextMenu={mockContextMenu}
        loading={false}
        error={null}
      />,
    );

    const rows = screen.getAllByRole("row").slice(1);
    const user = userEvent.setup();
    await user.pointer({ keys: "[MouseRight]", target: rows[0] });

    expect(mockContextMenu).toHaveBeenCalledWith(plan);
  });
});
