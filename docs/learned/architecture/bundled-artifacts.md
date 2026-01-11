---
title: Bundled Artifacts System
read_when:
  - understanding artifact syncing
  - working with BUNDLED_* registries
  - debugging erk sync
---

# Bundled Artifacts System

Erk bundles artifacts that are synced to projects during `erk init` or `erk sync`.

## Registry Location

`src/erk/artifacts/artifact_health.py` defines the bundled artifact registries:

| Registry            | Contents                                                |
| ------------------- | ------------------------------------------------------- |
| `BUNDLED_SKILLS`    | `dignified-python`, `learned-docs`, `erk-diff-analysis` |
| `BUNDLED_AGENTS`    | `devrun`                                                |
| `BUNDLED_WORKFLOWS` | `erk-impl.yml`                                          |
| `BUNDLED_ACTIONS`   | `setup-claude-code`, `setup-claude-erk`                 |
| `BUNDLED_HOOKS`     | `user-prompt-hook`, `exit-plan-mode-hook`               |

## Bundled vs Capability

| Aspect           | Bundled Artifacts       | Capabilities              |
| ---------------- | ----------------------- | ------------------------- |
| Installed via    | `erk init` / `erk sync` | `erk init capability add` |
| Always installed | Yes (if in registry)    | Only if `required=True`   |
| User opt-in      | No                      | Yes                       |
| Use case         | Core functionality      | Optional features         |

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
