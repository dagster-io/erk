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

Create `src/erk/capabilities/workflows/my_workflow.py`:

```python
"""MyWorkflowCapability - GitHub Action for specific purpose."""

import shutil
from pathlib import Path

from erk.core.capabilities.base import (
    Capability,
    CapabilityArtifact,
    CapabilityResult,
    CapabilityScope,
    ManagedArtifact,
)


class MyWorkflowCapability(Capability):
    """GitHub Action for specific purpose.

    Installs:
    - .github/workflows/my-workflow.yml
    """

    @property
    def name(self) -> str:
        return "my-workflow"

    @property
    def description(self) -> str:
        return "GitHub Action for specific purpose"

    @property
    def scope(self) -> CapabilityScope:
        return "project"

    @property
    def installation_check_description(self) -> str:
        return ".github/workflows/my-workflow.yml exists"

    @property
    def artifacts(self) -> list[CapabilityArtifact]:
        return [
            CapabilityArtifact(
                path=".github/workflows/my-workflow.yml",
                artifact_type="file",
            ),
        ]

    @property
    def managed_artifacts(self) -> list[ManagedArtifact]:
        """Declare workflow as managed artifact."""
        return [ManagedArtifact(name="my-workflow", artifact_type="workflow")]

    def is_installed(self, repo_root: Path | None) -> bool:
        assert repo_root is not None, "MyWorkflowCapability requires repo_root"
        return (repo_root / ".github" / "workflows" / "my-workflow.yml").exists()

    def install(self, repo_root: Path | None) -> CapabilityResult:
        assert repo_root is not None, "MyWorkflowCapability requires repo_root"
        from erk.artifacts.state import add_installed_capability
        from erk.artifacts.sync import get_bundled_github_dir

        bundled_github_dir = get_bundled_github_dir()
        if not bundled_github_dir.exists():
            return CapabilityResult(
                success=False,
                message="Bundled .github/ not found in erk package",
            )

        workflow_src = bundled_github_dir / "workflows" / "my-workflow.yml"
        if not workflow_src.exists():
            return CapabilityResult(
                success=False,
                message="my-workflow.yml not found in erk package",
            )

        workflow_dst = repo_root / ".github" / "workflows" / "my-workflow.yml"
        workflow_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(workflow_src, workflow_dst)

        # Record capability installation
        add_installed_capability(repo_root, self.name)

        return CapabilityResult(
            success=True,
            message="Installed my-workflow workflow",
        )

    def uninstall(self, repo_root: Path | None) -> CapabilityResult:
        """Remove the workflow."""
        assert repo_root is not None, "MyWorkflowCapability requires repo_root"
        from erk.artifacts.state import remove_installed_capability

        workflow_file = repo_root / ".github" / "workflows" / "my-workflow.yml"

        # Remove from installed capabilities
        remove_installed_capability(repo_root, self.name)

        if not workflow_file.exists():
            return CapabilityResult(
                success=True,
                message="my-workflow not installed",
            )

        workflow_file.unlink()
        return CapabilityResult(
            success=True,
            message="Removed .github/workflows/my-workflow.yml",
        )
```

### Step 2: Register in Registry

In `src/erk/core/capabilities/registry.py`:

1. Add import at top:

```python
from erk.capabilities.workflows.my_workflow import MyWorkflowCapability
```

2. Add instance to `_all_capabilities()` tuple:

```python
@cache
def _all_capabilities() -> tuple[Capability, ...]:
    return (
        # ... existing capabilities ...
        MyWorkflowCapability(),
    )
```

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
