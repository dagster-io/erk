---
title: Bundled Artifacts System
read_when:
  - understanding artifact syncing
  - working with managed artifacts
  - debugging erk sync
last_audited: "2026-02-05 14:17 PT"
audit_result: edited
---

# Bundled Artifacts System

Erk bundles artifacts that are synced to projects during `erk init` or `erk sync`.

## Artifact Management Architecture

Artifact management is unified through the capability system. Each capability declares what artifacts it manages via the `managed_artifacts` property, making the registry the single source of truth.

### How It Works

1. **Capabilities declare artifacts**: Each capability class has a `managed_artifacts` property returning `list[ManagedArtifact]`
2. **Registry aggregates**: `get_managed_artifacts()` collects all declarations into a single mapping
3. **Detection queries registry**: `is_capability_managed(name, type)` checks if an artifact is erk-managed

See `src/erk/core/capabilities/registry.py` for `get_managed_artifacts()` and `is_capability_managed()`. See `src/erk/core/capabilities/base.py` for `ManagedArtifactType` (the 8 valid artifact types: skill, command, agent, workflow, action, hook, prompt, review).

For examples of capabilities declaring managed artifacts, see `SkillCapability.managed_artifacts` in `src/erk/core/capabilities/skill_capability.py` and `HooksCapability.managed_artifacts` in `src/erk/capabilities/hooks.py`.

## Capability Installation

| Aspect          | Required Capabilities  | Optional Capabilities     |
| --------------- | ---------------------- | ------------------------- |
| Installed via   | `erk init` (automatic) | `erk init capability add` |
| `required` prop | `True`                 | `False`                   |
| User opt-in     | No                     | Yes                       |
| Example         | `erk-hooks`            | `dignified-python`        |

## How Bundling Works

### Editable Install (Development)

Files are read directly from repo root via `get_bundled_claude_dir()` and `get_bundled_github_dir()` in `src/erk/artifacts/paths.py`.

### Wheel Install (Production)

Files bundled at `erk/data/`:

| Bundled Path       | Source     |
| ------------------ | ---------- |
| `erk/data/claude/` | `.claude/` |
| `erk/data/github/` | `.github/` |

Configured in `pyproject.toml` via `force-include`.

## Sync and Health

`src/erk/artifacts/sync.py` provides `sync_artifacts()` (main sync entry point). `src/erk/artifacts/artifact_health.py` provides health checking functions (`find_orphaned_artifacts()`, `find_missing_artifacts()`, `get_artifact_health()`) with four status types: `up-to-date`, `changed-upstream`, `locally-modified`, `not-installed`.

These health functions accept bundled paths as keyword-only parameters (e.g., `bundled_claude_dir`, `bundled_github_dir`) rather than calling `get_bundled_*_dir()` internally. Call sites (CLI commands, health checks) resolve paths at the boundary and pass them in. See [Parameter Injection Pattern](../testing/parameter-injection-pattern.md) for details.

## Related Topics

- [Capability System Architecture](capability-system.md) - Optional features installed via capabilities
- [Workflow Capability Pattern](workflow-capability-pattern.md) - Pattern for workflow capabilities
