---
title: Adding Workflow Capabilities
read_when:
  - "adding workflow capabilities"
  - "creating GitHub Actions workflow capabilities"
  - "understanding workflow capability pattern"
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

See `src/erk/capabilities/workflows/learn.py` for the canonical pattern. Workflow capabilities extend `Capability` directly and implement:

- `name`, `description`, `scope` - Identity properties
- `artifacts`, `managed_artifacts` - Track installed files
- `is_installed()` - Check if workflow file exists
- `install()` - Copy from bundled artifacts, record installation
- `uninstall()` - Remove workflow file, clear installation record

Key patterns from the canonical example:

- Use `get_bundled_github_dir()` to find source files
- Create parent directories with `mkdir(parents=True, exist_ok=True)`
- Use `shutil.copy2()` to preserve file metadata
- Record state with `add_installed_capability()`

### Step 2: Register in Registry

In `src/erk/core/capabilities/registry.py`:

1. Add import at top of file
2. Add instance to the `_all_capabilities()` tuple

See `src/erk/core/capabilities/registry.py` for the registration pattern.

### Step 3: Bundle the Workflow File

The workflow YAML must exist in bundled artifacts:

```
src/erk/bundled/.github/workflows/my-workflow.yml
```

## Why No Template Base Class?

Unlike skills, reminders, and reviews, workflows:

- Have varied installation patterns (single file, multiple files, etc.)
- May require preflight checks for dependencies
- Often have unique error handling requirements
- Need custom validation logic

Each workflow capability is different enough that a template would add complexity without significant benefit.

## Example: LearnWorkflowCapability

See `src/erk/capabilities/workflows/learn.py` for a complete example.

Key patterns:

- Uses `get_bundled_github_dir()` to find source files
- Creates parent directories with `mkdir(parents=True, exist_ok=True)`
- Uses `shutil.copy2()` to preserve file metadata
- Records installation state with `add_installed_capability()`

## Testing

```bash
# List capabilities to verify registration
erk init capability list

# Check if installed
erk init capability status my-workflow

# Install
erk init capability install my-workflow

# Uninstall
erk init capability uninstall my-workflow
```

## Checklist

- [ ] File created at `src/erk/capabilities/workflows/<name>.py`
- [ ] Class extends `Capability` directly
- [ ] All required properties implemented
- [ ] `is_installed()` checks for workflow file
- [ ] `install()` copies from bundled artifacts
- [ ] `uninstall()` removes the workflow file
- [ ] Import added to `registry.py`
- [ ] Instance added to `_all_capabilities()` tuple
- [ ] Bundled workflow exists at `src/erk/bundled/.github/workflows/<name>.yml`

## Related Documentation

- [Folder Structure](folder-structure.md) - Where capability files go
- [Adding New Capabilities](adding-new-capabilities.md) - General capability pattern
