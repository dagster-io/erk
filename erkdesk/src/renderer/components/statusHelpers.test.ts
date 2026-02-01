import { describe, it, expect } from "vitest";
import type { PlanRow } from "../../types/erkdesk";
import {
  derivePrStatus,
  deriveChecksStatus,
  deriveCommentsStatus,
} from "./statusHelpers";

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
    run_url: null,
    worktree_branch: null,
    pr_head_branch: null,
    run_status: null,
    run_conclusion: null,
    resolved_comment_count: 0,
    total_comment_count: 0,
    ...overrides,
  };
}

describe("derivePrStatus", () => {
  it("returns gray with dash when no PR exists", () => {
    const plan = makePlan({ pr_number: null, pr_state: null });
    const status = derivePrStatus(plan);

    expect(status).toEqual({
      color: "gray",
      text: "—",
      tooltip: "No PR",
    });
  });

  it("returns green for open PR", () => {
    const plan = makePlan({ pr_number: 123, pr_state: "open" });
    const status = derivePrStatus(plan);

    expect(status).toEqual({
      color: "green",
      text: "#123",
      tooltip: "PR is open",
    });
  });

  it("returns amber for draft PR", () => {
    const plan = makePlan({ pr_number: 456, pr_state: "draft" });
    const status = derivePrStatus(plan);

    expect(status).toEqual({
      color: "amber",
      text: "#456",
      tooltip: "PR is in draft",
    });
  });

  it("returns purple for merged PR", () => {
    const plan = makePlan({ pr_number: 789, pr_state: "merged" });
    const status = derivePrStatus(plan);

    expect(status).toEqual({
      color: "purple",
      text: "#789",
      tooltip: "PR is merged",
    });
  });

  it("returns red for closed PR", () => {
    const plan = makePlan({ pr_number: 101, pr_state: "closed" });
    const status = derivePrStatus(plan);

    expect(status).toEqual({
      color: "red",
      text: "#101",
      tooltip: "PR is closed",
    });
  });

  it("returns gray for unknown PR state", () => {
    const plan = makePlan({ pr_number: 202, pr_state: "unknown" });
    const status = derivePrStatus(plan);

    expect(status).toEqual({
      color: "gray",
      text: "#202",
      tooltip: "PR status unknown",
    });
  });
});

describe("deriveChecksStatus", () => {
  it("returns gray with dash when no checks exist", () => {
    const plan = makePlan({ run_status: null, run_conclusion: null });
    const status = deriveChecksStatus(plan);

    expect(status).toEqual({
      color: "gray",
      text: "—",
      tooltip: "No checks",
    });
  });

  it("returns amber when checks are in progress", () => {
    const plan = makePlan({ run_status: "in_progress", run_conclusion: null });
    const status = deriveChecksStatus(plan);

    expect(status).toEqual({
      color: "amber",
      text: "⋯",
      tooltip: "Checks running",
    });
  });

  it("returns amber when checks are queued", () => {
    const plan = makePlan({ run_status: "queued", run_conclusion: null });
    const status = deriveChecksStatus(plan);

    expect(status).toEqual({
      color: "amber",
      text: "⋯",
      tooltip: "Checks running",
    });
  });

  it("returns green for successful checks", () => {
    const plan = makePlan({ run_status: "completed", run_conclusion: "success" });
    const status = deriveChecksStatus(plan);

    expect(status).toEqual({
      color: "green",
      text: "✓",
      tooltip: "Checks passed",
    });
  });

  it("returns red for failed checks", () => {
    const plan = makePlan({ run_status: "completed", run_conclusion: "failure" });
    const status = deriveChecksStatus(plan);

    expect(status).toEqual({
      color: "red",
      text: "✗",
      tooltip: "Checks failed",
    });
  });

  it("returns gray for cancelled checks", () => {
    const plan = makePlan({ run_status: "completed", run_conclusion: "cancelled" });
    const status = deriveChecksStatus(plan);

    expect(status).toEqual({
      color: "gray",
      text: "✗",
      tooltip: "Checks cancelled",
    });
  });

  it("returns gray for skipped checks", () => {
    const plan = makePlan({ run_status: "completed", run_conclusion: "skipped" });
    const status = deriveChecksStatus(plan);

    expect(status).toEqual({
      color: "gray",
      text: "—",
      tooltip: "Checks skipped",
    });
  });

  it("returns red for timed out checks", () => {
    const plan = makePlan({ run_status: "completed", run_conclusion: "timed_out" });
    const status = deriveChecksStatus(plan);

    expect(status).toEqual({
      color: "red",
      text: "✗",
      tooltip: "Checks timed out",
    });
  });

  it("returns gray for unknown conclusion", () => {
    const plan = makePlan({ run_status: "completed", run_conclusion: "unknown" });
    const status = deriveChecksStatus(plan);

    expect(status).toEqual({
      color: "gray",
      text: "?",
      tooltip: "Checks status: unknown",
    });
  });
});

describe("deriveCommentsStatus", () => {
  it("returns gray with dash when no comments exist", () => {
    const plan = makePlan({
      resolved_comment_count: 0,
      total_comment_count: 0,
    });
    const status = deriveCommentsStatus(plan);

    expect(status).toEqual({
      color: "gray",
      text: "—",
      tooltip: "No comments",
    });
  });

  it("returns green when all comments are resolved", () => {
    const plan = makePlan({
      resolved_comment_count: 5,
      total_comment_count: 5,
    });
    const status = deriveCommentsStatus(plan);

    expect(status).toEqual({
      color: "green",
      text: "5/5",
      tooltip: "All comments resolved",
    });
  });

  it("returns amber when some comments are unresolved", () => {
    const plan = makePlan({
      resolved_comment_count: 3,
      total_comment_count: 7,
    });
    const status = deriveCommentsStatus(plan);

    expect(status).toEqual({
      color: "amber",
      text: "3/7",
      tooltip: "4 unresolved",
    });
  });

  it("returns amber when no comments are resolved", () => {
    const plan = makePlan({
      resolved_comment_count: 0,
      total_comment_count: 3,
    });
    const status = deriveCommentsStatus(plan);

    expect(status).toEqual({
      color: "amber",
      text: "0/3",
      tooltip: "3 unresolved",
    });
  });

  it("correctly calculates unresolved count", () => {
    const plan = makePlan({
      resolved_comment_count: 1,
      total_comment_count: 2,
    });
    const status = deriveCommentsStatus(plan);

    expect(status).toEqual({
      color: "amber",
      text: "1/2",
      tooltip: "1 unresolved",
    });
  });
});
