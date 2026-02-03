---
title: Bundled Artifacts System
read_when:
  - understanding artifact syncing
  - working with managed artifacts
  - debugging erk sync
---

# Bundled Artifacts System

Erk bundles artifacts that are synced to projects during `erk init` or `erk sync`.

## Artifact Management Architecture

Artifact management is now unified through the capability system. Each capability declares what artifacts it manages via the `managed_artifacts` property, making the registry the single source of truth.

### How It Works

1. **Capabilities declare artifacts**: Each capability class has a `managed_artifacts` property returning `list[ManagedArtifact]`
2. **Registry aggregates**: `get_managed_artifacts()` collects all declarations into a single mapping
3. **Detection queries registry**: `is_capability_managed(name, type)` checks if an artifact is erk-managed

### Registry Functions

`src/erk/core/capabilities/registry.py` provides:

| Function                            | Purpose                                         |
| ----------------------------------- | ----------------------------------------------- |
| `get_managed_artifacts()`           | Returns `dict[(name, type), capability_name]`   |
| `is_capability_managed(name, type)` | Check if artifact is declared by any capability |

### Artifact Types

The `ManagedArtifactType` literal defines valid artifact types:

| Type       | Example Artifact                          |
| ---------- | ----------------------------------------- |
| `skill`    | `dignified-python`, `fake-driven-testing` |
| `command`  | Claude commands                           |
| `agent`    | `devrun`                                  |
| `workflow` | `plan-implement`, `learn`                 |
| `action`   | `setup-claude-code`, `setup-claude-erk`   |
| `hook`     | `user-prompt-hook`, `exit-plan-mode-hook` |
| `prompt`   | `.github/prompts/` files                  |
| `review`   | `.github/reviews/` files                  |

### Example: SkillCapability

Each `SkillCapability` returns a single artifact for its skill name. See `src/erk/core/capabilities/skill_capability.py:62-64` for the implementation.

### Example: HooksCapability

The hooks capability declares its managed hook artifacts. See `src/erk/capabilities/hooks.py:55-60` for the implementation.

## Capability Installation

| Aspect          | Required Capabilities  | Optional Capabilities     |
| --------------- | ---------------------- | ------------------------- |
| Installed via   | `erk init` (automatic) | `erk init capability add` |
| `required` prop | `True`                 | `False`                   |
| User opt-in     | No                     | Yes                       |
| Example         | `erk-hooks`            | `dignified-python`        |

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

## Codex Portability Classification

Erk classifies skills into two tiers for external distribution:

### Codex-Portable Skills

Skills that work with any AI coding agent. These have no Claude-specific dependencies (hooks, session logs, Claude Code commands).

See `CODEX_PORTABLE_SKILLS` in `src/erk/core/capabilities/codex_portable.py` for the authoritative list.

**Portability Criteria:**

- No Claude-specific hook dependencies
- No session log parsing or storage
- No Claude Code slash commands
- YAML frontmatter with `name` (<=64 chars) and `description` (<=1024 chars)

### Claude-Only Skills

Skills requiring Claude-specific features. These cannot be ported.

See `CLAUDE_ONLY_SKILLS` in `src/erk/core/capabilities/codex_portable.py` for the list (4 skills).

**Why Claude-only:** Session inspection, CI iteration hooks, command/skill creators that output Claude format

### Bundled Path Resolution

| Install Type | `get_bundled_codex_dir()` Returns |
| ------------ | --------------------------------- |
| Wheel        | `erk/data/codex/`                 |
| Editable     | `.claude/` (shared with Claude)   |

See `get_bundled_codex_dir()` in `src/erk/artifacts/paths.py` for the implementation.

### Adding a New Codex-Portable Skill

1. Create skill in `.claude/skills/<name>/SKILL.md` with required frontmatter
2. Add skill name to `CODEX_PORTABLE_SKILLS` in `src/erk/core/capabilities/codex_portable.py`
3. Add force-include mapping in `pyproject.toml` under `[tool.hatch.build.targets.wheel.force-include]`
4. Run tests: `pytest tests/unit/artifacts/test_codex_compatibility.py`

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
