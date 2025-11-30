"""Shared constants for erk CLI commands."""

# GitHub issue label for erk plans
ERK_PLAN_LABEL = "erk-plan"

# Feature flag: Use GitHub's native branch linking via `gh issue develop`
# When True: Uses `gh issue develop` to create branches linked to issues
#            (appears in issue sidebar under "Development")
# When False: Uses traditional branch naming with derive_branch_name_with_date()
USE_GITHUB_NATIVE_BRANCH_LINKING = True

# GitHub Actions workflow for remote implementation dispatch
DISPATCH_WORKFLOW_NAME = "dispatch-erk-queue-git.yml"
DISPATCH_WORKFLOW_METADATA_NAME = "dispatch-erk-queue-git"
