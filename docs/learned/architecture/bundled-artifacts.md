---
title: Bundled Artifacts System
read_when:
  - understanding artifact syncing
  - working with managed artifacts
  - debugging erk sync
---

# Bundled Artifacts System

Erk bundles artifacts that are synced to projects during `erk init` or `erk sync`.

## Registry Architecture

The capability system is the single source of truth for artifact management. Each capability declares which artifacts it manages via the `managed_artifacts` property.

### How It Works

1. Each capability class declares `managed_artifacts` property returning `list[ManagedArtifact]`
2. Registry provides `get_managed_artifacts()` - returns all managed artifact mappings
3. Registry provides `is_capability_managed(name, type)` - checks if artifact is managed
4. `_get_bundled_by_type()` helper in `artifact_health.py` derives sets from capabilities

### Key Types

From `src/erk/core/capabilities/base.py`:

```python
ManagedArtifactType = Literal["skill", "command", "agent", "workflow", "action", "hook", "prompt"]

@dataclass(frozen=True)
class ManagedArtifact:
    name: str  # e.g., "dignified-python", "ruff-format-hook"
    artifact_type: ManagedArtifactType
```

### Registry Functions

From `src/erk/core/capabilities/registry.py`:

| Function                            | Purpose                                         |
| ----------------------------------- | ----------------------------------------------- |
| `get_managed_artifacts()`           | Returns dict mapping (name, type) -> capability |
| `is_capability_managed(name, type)` | Check if artifact is declared as managed        |

### Detection Logic

From `src/erk/artifacts/artifact_health.py`:

```python
def is_erk_managed(artifact: InstalledArtifact) -> bool:
    # Commands use prefix matching (not capability-declared)
    if artifact.artifact_type == "command":
        return artifact.name.startswith("erk:")
    # All other artifacts: query capabilities as single source of truth
    return is_capability_managed(artifact.name, artifact.artifact_type)
```

## Capability-Managed Artifacts

Capabilities declare their managed artifacts. Examples:

| Capability                  | Managed Artifacts                                        |
| --------------------------- | -------------------------------------------------------- |
| `DignifiedPythonCapability` | `dignified-python` (skill)                               |
| `HooksCapability`           | `user-prompt-submit-hook`, `exit-plan-mode-hook` (hooks) |
| `DevrunAgentCapability`     | `devrun` (agent)                                         |
| `ErkImplWorkflowCapability` | `erk-impl.yml` (workflow), setup actions                 |

See [Capability System Architecture](capability-system.md) for the full capability registry.

## How Bundling Works

### Editable Install (Development)

Files are read directly from repo root via `get_bundled_claude_dir()` and `get_bundled_github_dir()` in `src/erk/artifacts/sync.py`.

### Wheel Install (Production)

Files bundled at `erk/data/`:

| Bundled Path       | Source     |
| ------------------ | ---------- |
| `erk/data/claude/` | `.claude/` |
| `erk/data/github/` | `.github/` |

Configured in `pyproject.toml` via `force-include`.

## Sync Functions

The `src/erk/artifacts/sync.py` module provides:

| Function                   | Purpose                                 |
| -------------------------- | --------------------------------------- |
| `sync_artifacts()`         | Main sync, copies all bundled artifacts |
| `get_bundled_claude_dir()` | Get path to bundled `.claude/`          |
| `get_bundled_github_dir()` | Get path to bundled `.github/`          |

## Health Checks

`src/erk/artifacts/artifact_health.py` provides health checking functions:

| Function                    | Purpose                        |
| --------------------------- | ------------------------------ |
| `find_orphaned_artifacts()` | Files in project not in bundle |
| `find_missing_artifacts()`  | Files in bundle not in project |
| `get_artifact_health()`     | Per-artifact status comparison |

### Artifact Status Types

| Status             | Meaning                          |
| ------------------ | -------------------------------- |
| `up-to-date`       | Hash and version match           |
| `changed-upstream` | Erk version updated the artifact |
| `locally-modified` | User modified the artifact       |
| `not-installed`    | Artifact not present locally     |

## Related Topics

- [Capability System Architecture](capability-system.md) - Optional features installed via capabilities
- [Workflow Capability Pattern](workflow-capability-pattern.md) - Pattern for workflow capabilities
