import type { PlanRow } from "../../types/erkdesk";
import type { StatusColor } from "./StatusIndicator";

export interface StatusInfo {
  color: StatusColor;
  text: string;
  tooltip: string;
}

/**
 * Derive PR status from pr_state and pr_number
 */
export function derivePrStatus(plan: PlanRow): StatusInfo {
  if (plan.pr_number === null) {
    return {
      color: "gray",
      text: "—",
      tooltip: "No PR",
    };
  }

  const prText = `#${plan.pr_number}`;

  switch (plan.pr_state) {
    case "open":
      return {
        color: "green",
        text: prText,
        tooltip: "PR is open",
      };
    case "draft":
      return {
        color: "amber",
        text: prText,
        tooltip: "PR is in draft",
      };
    case "merged":
      return {
        color: "purple",
        text: prText,
        tooltip: "PR is merged",
      };
    case "closed":
      return {
        color: "red",
        text: prText,
        tooltip: "PR is closed",
      };
    default:
      return {
        color: "gray",
        text: prText,
        tooltip: "PR status unknown",
      };
  }
}

/**
 * Derive checks status from run_status and run_conclusion
 */
export function deriveChecksStatus(plan: PlanRow): StatusInfo {
  // If checks are running
  if (plan.run_status === "in_progress" || plan.run_status === "queued") {
    return {
      color: "amber",
      text: "⋯",
      tooltip: "Checks running",
    };
  }

  // If checks completed, check conclusion
  if (plan.run_conclusion !== null) {
    switch (plan.run_conclusion) {
      case "success":
        return {
          color: "green",
          text: "✓",
          tooltip: "Checks passed",
        };
      case "failure":
        return {
          color: "red",
          text: "✗",
          tooltip: "Checks failed",
        };
      case "cancelled":
        return {
          color: "gray",
          text: "✗",
          tooltip: "Checks cancelled",
        };
      case "skipped":
        return {
          color: "gray",
          text: "—",
          tooltip: "Checks skipped",
        };
      case "timed_out":
        return {
          color: "red",
          text: "✗",
          tooltip: "Checks timed out",
        };
      default:
        return {
          color: "gray",
          text: "?",
          tooltip: `Checks status: ${plan.run_conclusion}`,
        };
    }
  }

  // No checks data
  return {
    color: "gray",
    text: "—",
    tooltip: "No checks",
  };
}

/**
 * Derive comments status from resolved_comment_count and total_comment_count
 */
export function deriveCommentsStatus(plan: PlanRow): StatusInfo {
  const { resolved_comment_count, total_comment_count } = plan;

  // No comments
  if (total_comment_count === 0) {
    return {
      color: "gray",
      text: "—",
      tooltip: "No comments",
    };
  }

  const text = `${resolved_comment_count}/${total_comment_count}`;

  // All resolved
  if (resolved_comment_count === total_comment_count) {
    return {
      color: "green",
      text,
      tooltip: "All comments resolved",
    };
  }

  // Partially resolved
  return {
    color: "amber",
    text,
    tooltip: `${total_comment_count - resolved_comment_count} unresolved`,
  };
}
