"""Shared constants for erk CLI commands."""

# Title prefix for erk-pr issues (with trailing space for easy stripping)
ERK_PR_TITLE_PREFIX = "[erk-pr] "

# Plan markdown heading prefix (with trailing space for easy stripping)
PLAN_HEADING_PREFIX = "Plan: "

# PR title prefix for plan-originated PRs
PLANNED_PR_TITLE_PREFIX = "plnd/"

# GitHub Actions workflow for remote implementation dispatch
DISPATCH_WORKFLOW_NAME = "plan-implement.yml"
DISPATCH_WORKFLOW_METADATA_NAME = "plan-implement"

# GitHub Actions workflow for remote rebase with conflict resolution
REBASE_WORKFLOW_NAME = "pr-rebase.yml"

# GitHub Actions workflow for remote PR comment addressing
PR_ADDRESS_WORKFLOW_NAME = "pr-address.yml"

# GitHub Actions workflow for remote PR rewrite (rebase + AI PR summary)
PR_REWRITE_WORKFLOW_NAME = "pr-rewrite.yml"

# GitHub Actions workflow for one-shot autonomous execution
ONE_SHOT_WORKFLOW_NAME = "one-shot.yml"

# GitHub Actions workflow for consolidating learn plans
CONSOLIDATE_LEARN_PLANS_WORKFLOW_NAME = "consolidate-learn-plans.yml"

# Workflow command name to actual workflow filename mapping
# This provides a unified interface via `erk launch <name>`
WORKFLOW_COMMAND_MAP: dict[str, str] = {
    "plan-implement": DISPATCH_WORKFLOW_NAME,  # plan-implement.yml
    "pr-rebase": REBASE_WORKFLOW_NAME,  # pr-rebase.yml
    "pr-address": PR_ADDRESS_WORKFLOW_NAME,  # pr-address.yml
    "pr-rewrite": PR_REWRITE_WORKFLOW_NAME,  # pr-rewrite.yml
    "learn": "learn.yml",
    "one-shot": ONE_SHOT_WORKFLOW_NAME,  # one-shot.yml
    "consolidate-learn-plans": CONSOLIDATE_LEARN_PLANS_WORKFLOW_NAME,
}

# Workflow names that trigger the autofix workflow
# Must match the `name:` field in each .yml file (which should match filename without .yml)
AUTOFIX_TRIGGER_WORKFLOWS = frozenset(
    {
        "python-format",
        "lint",
        "docs-check",
        "markdown-format",
    }
)

# Shared label for all plan PRs (implementation + learn)
ERK_PR_LABEL = "erk-pr"

# Learn plan label (for plans that learn from sessions)
ERK_LEARN_LABEL = "erk-learn"

ERK_LEARN_LABEL_DESCRIPTION = "Documentation learning PR"
ERK_LEARN_LABEL_COLOR = "D93F0B"  # Orange-red
