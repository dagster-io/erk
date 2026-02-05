---
title: Adding Workflow Capabilities
read_when:
  - "adding workflow capabilities"
  - "creating GitHub Actions workflow capabilities"
  - "understanding workflow capability pattern"
last_audited: "2026-02-05 13:55 PT"
audit_result: edited
---

# Adding Workflow Capabilities

Workflows are capabilities that install GitHub Actions workflow files. They are standalone capabilities (no template base class) because each workflow has unique installation logic.

## Overview

Workflow capabilities:

- Install `.github/workflows/<name>.yml` files
- Are project-level (require repo context)
- Extend `Capability` directly (no template)
- Require full method implementations

## File Location

```
src/erk/capabilities/workflows/<workflow_name>.py
```

## Implementation

### Step 1: Create the Capability File

Create `src/erk/capabilities/workflows/my_workflow.py`.

See `LearnWorkflowCapability` in `src/erk/capabilities/workflows/learn.py` for the canonical single-file pattern, and `ErkImplWorkflowCapability` in `src/erk/capabilities/workflows/erk_impl.py` for a multi-artifact pattern. Workflow capabilities extend `Capability` directly and implement all abstract members from `src/erk/core/capabilities/base.py`:

- `name`, `description`, `scope`, `installation_check_description` - Identity properties
- `artifacts`, `managed_artifacts` - Track installed files
- `is_installed()` - Check if workflow file exists
- `install()` - Copy from bundled artifacts, record installation
- `uninstall()` - Remove workflow file, clear installation record

### Step 2: Register in Registry

In `src/erk/core/capabilities/registry.py`, add an import and add an instance to the `_all_capabilities()` tuple.

### Step 3: Add the Workflow File

The workflow YAML must exist in a location resolved by `get_bundled_github_dir()` (see `src/erk/artifacts/paths.py`). For editable installs this is the repo root `.github/` directory; for wheel installs it is `erk/data/github/`. Place the workflow file at `.github/workflows/<name>.yml` in the repo.

## Why No Template Base Class?

Unlike skills, reminders, and reviews, workflows:

- Have varied installation patterns (single file, multiple files, etc.)
- May require preflight checks for dependencies
- Often have unique error handling requirements
- Need custom validation logic

Each workflow capability is different enough that a template would add complexity without significant benefit.

## Testing

```bash
# List capabilities to verify registration
erk init capability list

# Check detailed status for a specific capability
erk init capability list my-workflow

# Install
erk init capability add my-workflow

# Remove
erk init capability remove my-workflow
```

## Checklist

- [ ] File created at `src/erk/capabilities/workflows/<name>.py`
- [ ] Class extends `Capability` directly
- [ ] All abstract properties implemented (including `installation_check_description`)
- [ ] `is_installed()` checks for workflow file
- [ ] `install()` copies from bundled artifacts via `get_bundled_github_dir()`
- [ ] `uninstall()` removes the workflow file
- [ ] Import added to `registry.py`
- [ ] Instance added to `_all_capabilities()` tuple
- [ ] Workflow YAML exists at `.github/workflows/<name>.yml`

## Related Documentation

- [Folder Structure](folder-structure.md) - Where capability files go
- [Adding New Capabilities](adding-new-capabilities.md) - General capability pattern
