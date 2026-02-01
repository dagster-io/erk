import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { PlanRow } from "../types/erkdesk";
import App from "./App";

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

describe("App", () => {
  beforeEach(() => {
    vi.mocked(window.erkdesk.fetchPlans).mockReset();
    vi.mocked(window.erkdesk.loadWebViewURL).mockReset();
    vi.mocked(window.erkdesk.updateWebViewBounds).mockReset();
    vi.mocked(window.erkdesk.executeAction).mockReset();
  });

  it("renders loading state initially", () => {
    vi.mocked(window.erkdesk.fetchPlans).mockReturnValue(new Promise(() => {}));
    render(<App />);
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

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText("Alpha")).toBeInTheDocument();
    });
    expect(screen.getByText("Beta")).toBeInTheDocument();
  });

  it("renders error message on fetch failure", async () => {
    vi.mocked(window.erkdesk.fetchPlans).mockResolvedValue({
      success: false,
      plans: [],
      count: 0,
      error: "Network timeout",
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText("Error: Network timeout")).toBeInTheDocument();
    });
  });

  it("renders toolbar with action buttons", async () => {
    vi.mocked(window.erkdesk.fetchPlans).mockResolvedValue({
      success: true,
      plans: [makePlan()],
      count: 1,
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText("Submit")).toBeInTheDocument();
    });
    expect(screen.getByText("Land")).toBeInTheDocument();
    expect(screen.getByText("Close")).toBeInTheDocument();
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

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText("First")).toBeInTheDocument();
    });

    const rows = screen.getAllByRole("row").slice(1);
    expect(rows[0]).toHaveClass("plan-list__row--selected");

    const user = userEvent.setup();
    await user.keyboard("j");
    expect(rows[1]).toHaveClass("plan-list__row--selected");
    expect(rows[0]).not.toHaveClass("plan-list__row--selected");

    await user.keyboard("k");
    expect(rows[0]).toHaveClass("plan-list__row--selected");
  });

  it("loads URL for first plan on initial render", async () => {
    const plans = [
      makePlan({
        issue_number: 1,
        title: "First",
        issue_url: "https://github.com/org/repo/issues/1",
      }),
    ];
    vi.mocked(window.erkdesk.fetchPlans).mockResolvedValue({
      success: true,
      plans,
      count: 1,
    });

    render(<App />);

    await waitFor(() => {
      expect(window.erkdesk.loadWebViewURL).toHaveBeenCalledWith(
        "https://github.com/org/repo/issues/1",
      );
    });
  });

  it("prefers pr_url over issue_url", async () => {
    const plans = [
      makePlan({
        issue_number: 1,
        title: "With PR",
        issue_url: "https://github.com/org/repo/issues/1",
        pr_url: "https://github.com/org/repo/pull/42",
      }),
    ];
    vi.mocked(window.erkdesk.fetchPlans).mockResolvedValue({
      success: true,
      plans,
      count: 1,
    });

    render(<App />);

    await waitFor(() => {
      expect(window.erkdesk.loadWebViewURL).toHaveBeenCalledWith(
        "https://github.com/org/repo/pull/42",
      );
    });
    expect(window.erkdesk.loadWebViewURL).not.toHaveBeenCalledWith(
      "https://github.com/org/repo/issues/1",
    );
  });

  describe("auto-refresh", () => {
    beforeEach(() => {
      vi.useFakeTimers({ shouldAdvanceTime: true });
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it("preserves selection by issue_number after refresh", async () => {
      const initialPlans = [
        makePlan({ issue_number: 10, title: "Alpha" }),
        makePlan({ issue_number: 20, title: "Beta" }),
      ];
      const refreshedPlans = [
        makePlan({ issue_number: 20, title: "Beta" }),
        makePlan({ issue_number: 10, title: "Alpha" }),
      ];

      vi.mocked(window.erkdesk.fetchPlans)
        .mockResolvedValueOnce({
          success: true,
          plans: initialPlans,
          count: 2,
        })
        .mockResolvedValueOnce({
          success: true,
          plans: refreshedPlans,
          count: 2,
        });

      render(<App />);

      await waitFor(() => {
        expect(screen.getByText("Alpha")).toBeInTheDocument();
      });

      const rowsBefore = screen.getAllByRole("row").slice(1);
      expect(rowsBefore[0]).toHaveClass("plan-list__row--selected");

      await vi.advanceTimersByTimeAsync(15_000);

      await waitFor(() => {
        const rowsAfter = screen.getAllByRole("row").slice(1);
        expect(rowsAfter[1]).toHaveClass("plan-list__row--selected");
        expect(rowsAfter[0]).not.toHaveClass("plan-list__row--selected");
      });
    });

    it("errors during refresh don't replace data", async () => {
      const initialPlans = [makePlan({ issue_number: 1, title: "Keeper" })];

      vi.mocked(window.erkdesk.fetchPlans)
        .mockResolvedValueOnce({
          success: true,
          plans: initialPlans,
          count: 1,
        })
        .mockResolvedValueOnce({
          success: false,
          plans: [],
          count: 0,
          error: "Network error",
        });

      render(<App />);

      await waitFor(() => {
        expect(screen.getByText("Keeper")).toBeInTheDocument();
      });

      await vi.advanceTimersByTimeAsync(15_000);

      await waitFor(() => {
        expect(screen.getByText("Keeper")).toBeInTheDocument();
      });
      expect(screen.queryByText(/Error:/)).not.toBeInTheDocument();
    });
  });
});
