"""Shared constants for erk CLI commands."""

# GitHub issue label for erk plans
ERK_PLAN_LABEL = "erk-plan"

# GitHub Actions workflow for remote implementation dispatch
DISPATCH_WORKFLOW_NAME = "erk-impl.yml"
DISPATCH_WORKFLOW_METADATA_NAME = "erk-impl"

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

# Extraction plan label (for plans that extract documentation from sessions)
ERK_EXTRACTION_LABEL = "erk-extraction"
ERK_EXTRACTION_LABEL_DESCRIPTION = "Documentation extraction plan"
ERK_EXTRACTION_LABEL_COLOR = "D93F0B"  # Orange-red
