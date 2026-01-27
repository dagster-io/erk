---
title: Workflow Naming Conventions
read_when:
  - "creating new GitHub Actions workflows"
  - "understanding WORKFLOW_COMMAND_MAP"
  - "working with erk launch command"
---

# Workflow Naming Conventions

The `erk launch` command provides a unified CLI interface for triggering GitHub Actions workflows. The mapping between CLI command names and workflow filenames follows a consistent naming convention.

## WORKFLOW_COMMAND_MAP

The canonical mapping is defined in `src/erk/cli/constants.py`:

```python
WORKFLOW_COMMAND_MAP: dict[str, str] = {
    "plan-implement": "plan-implement.yml",
    "pr-fix-conflicts": "pr-fix-conflicts.yml",
    "pr-address": "pr-address.yml",
    "objective-reconcile": "objective-reconcile.yml",
    "learn": "learn.yml",
}
```

## Naming Convention

**Pattern**: CLI command name matches workflow filename (without `.yml` extension)

**Examples**:

- `erk launch pr-fix-conflicts` → `.github/workflows/pr-fix-conflicts.yml`
- `erk launch learn` → `.github/workflows/learn.yml`
- `erk launch objective-reconcile` → `.github/workflows/objective-reconcile.yml`

## Historical Context

Prior to PR #6087, the command was `erk workflow launch` and some workflow files had different names:

- `pr-fix-conflicts.yml` was called `erk-rebase.yml`
- `learn.yml` was called `learn-dispatch.yml`

The current convention eliminates this indirection - the CLI name directly maps to the filename.

## Adding New Workflows

When creating a new workflow that should be launchable via `erk launch`:

1. **Create workflow file**: `.github/workflows/<command-name>.yml`
2. **Update WORKFLOW_COMMAND_MAP**: Add entry in `src/erk/cli/constants.py`
3. **Set workflow name field**: The `name:` field in the YAML should match the command name (for discoverability)

Example:

```yaml
# .github/workflows/my-new-workflow.yml
name: my-new-workflow
on:
  workflow_dispatch:
    inputs:
      # ... inputs ...
```

```python
# src/erk/cli/constants.py
WORKFLOW_COMMAND_MAP: dict[str, str] = {
    # ... existing entries ...
    "my-new-workflow": "my-new-workflow.yml",
}
```

## Related Documentation

- [Workflow Commands](../cli/workflow-commands.md) - Usage guide for `erk launch`
- [Remote Workflow Template](../erk/remote-workflow-template.md) - Workflow YAML patterns
