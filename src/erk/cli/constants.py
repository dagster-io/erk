"""Shared constants for erk CLI commands."""

# GitHub issue label for erk plans
ERK_PLAN_LABEL = "erk-plan"

# Title prefix for erk-plan issues (with trailing space for easy stripping)
ERK_PLAN_TITLE_PREFIX = "[erk-plan] "

# Plan markdown heading prefix (with trailing space for easy stripping)
PLAN_HEADING_PREFIX = "Plan: "

# GitHub Actions workflow for remote implementation dispatch
DISPATCH_WORKFLOW_NAME = "erk-impl.yml"
DISPATCH_WORKFLOW_METADATA_NAME = "erk-impl"

# GitHub Actions workflow for remote rebase with conflict resolution
REBASE_WORKFLOW_NAME = "erk-rebase.yml"

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

# Documentation extraction tracking label
DOCS_EXTRACTED_LABEL = "docs-extracted"
DOCS_EXTRACTED_LABEL_DESCRIPTION = "Session logs analyzed for documentation improvements"
DOCS_EXTRACTED_LABEL_COLOR = "5319E7"  # Purple

# Learn plan label (for plans that learn from sessions)
ERK_LEARN_LABEL = "erk-learn"
ERK_LEARN_LABEL_DESCRIPTION = "Documentation learning plan"
ERK_LEARN_LABEL_COLOR = "D93F0B"  # Orange-red
