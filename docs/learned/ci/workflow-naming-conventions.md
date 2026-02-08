---
title: Workflow Naming Conventions
read_when:
  - "creating new GitHub Actions workflows launchable via erk launch"
  - "understanding the relationship between CLI names and workflow files"
tripwires:
  - action: "The CLI command name MUST match the workflow filename (witho..."
    warning: "The CLI command name MUST match the workflow filename (without .yml)"
  - action: "The workflow's name: field MUST match the CLI command name"
    warning: "The workflow's name: field MUST match the CLI command name"
  - action: "adding launchable workflows"
    warning: "Update WORKFLOW_COMMAND_MAP when adding launchable workflows"
---

# Workflow Naming Conventions

## Why Direct Name Mapping

<!-- Source: src/erk/cli/commands/launch_cmd.py, _get_workflow_file -->

The `erk launch` command uses **identity mapping** between CLI names and workflow files: the command name IS the filename (minus `.yml`). This eliminates indirection and makes the system self-documenting.

**Design rationale**: Early versions had arbitrary mappings (`erk workflow launch rebase` → `erk-rebase.yml`). This created two names for one thing. The current system enforces a single canonical name used everywhere.

## The Three-Way Name Consistency Rule

When a workflow is launchable via `erk launch`, three identifiers MUST match:

1. **CLI command name**: `erk launch pr-fix-conflicts`
2. **Workflow filename**: `.github/workflows/pr-fix-conflicts.yml`
3. **Workflow YAML `name:` field**: `name: pr-fix-conflicts`

**Why the `name:` field matters**: GitHub Actions uses this field for display in the UI and for workflow reference. Keeping it consistent with the CLI name ensures users see the same identifier everywhere.

**Anti-pattern**: Using descriptive `name:` fields like `name: "PR Conflict Resolution"` breaks discoverability. When users see "pr-fix-conflicts" in the CLI, they expect to find a workflow with that exact name in GitHub's UI.

## Adding New Launchable Workflows

<!-- Source: src/erk/cli/constants.py, WORKFLOW_COMMAND_MAP -->

**Two-place update pattern**:

1. Create workflow file with matching name: `.github/workflows/<command-name>.yml`
2. Add entry to `WORKFLOW_COMMAND_MAP` in `src/erk/cli/constants.py`

The map exists for **validation only** — it defines which workflows are launchable. The map doesn't perform translation; it just checks membership.

**Example workflow file header**:

```yaml
name: my-new-workflow
run-name: "my-new-workflow:${{ inputs.distinct_id }}"

on:
  workflow_dispatch:
    inputs:
      # ... inputs ...
```

**Example constant update**:

```python
WORKFLOW_COMMAND_MAP: dict[str, str] = {
    # ... existing entries ...
    "my-new-workflow": "my-new-workflow.yml",  # Identity mapping
}
```

## Historical Context

**Before PR #6087**:

- Command was `erk workflow launch` (now `erk launch`)
- Workflow files had different names than CLI commands:
  - `erk-rebase.yml` (now `pr-fix-conflicts.yml`)
  - `learn-dispatch.yml` (now `learn.yml`)

These renames eliminated the translation layer. The map still exists but now only serves as an allowlist.

## Decision: Why Not Auto-Discovery?

**Question**: Why maintain `WORKFLOW_COMMAND_MAP` at all? Why not discover workflow files automatically?

**Answer**: Explicit allowlist prevents accidental exposure of internal workflows. Not all workflows in `.github/workflows/` should be launchable via CLI (e.g., CI workflows, scheduled jobs, autofix workflows). The map defines the public API.

## See Also

<!-- Source: src/erk/cli/commands/launch_cmd.py, launch command -->

- The `erk launch` command implementation shows workflow-specific parameter handling
- Each launchable workflow has a dedicated trigger function (`_trigger_pr_fix_conflicts`, `_trigger_learn`, etc.)
