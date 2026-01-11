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

`src/erk/artifacts/artifact_health.py`:

```python
BUNDLED_SKILLS = frozenset({"dignified-python", "learned-docs", "erk-diff-analysis"})
BUNDLED_AGENTS = frozenset({"devrun"})
BUNDLED_WORKFLOWS = frozenset({"erk-impl.yml"})
BUNDLED_ACTIONS = frozenset({"setup-claude-code", "setup-claude-erk"})
BUNDLED_HOOKS = frozenset({"user-prompt-hook", "exit-plan-mode-hook"})
```

## Bundled vs Capability

| Aspect           | Bundled Artifacts       | Capabilities              |
| ---------------- | ----------------------- | ------------------------- |
| Installed via    | `erk init` / `erk sync` | `erk init capability add` |
| Always installed | Yes (if in registry)    | Only if required=True     |
| User opt-in      | No                      | Yes                       |
| Use case         | Core functionality      | Optional features         |

## How Bundling Works

### Editable Install (Development)

Files read directly from repo root:

- `.claude/` → `get_bundled_claude_dir()`
- `.github/` → `get_bundled_github_dir()`

### Wheel Install (Production)

Files bundled at `erk/data/`:

- `erk/data/claude/` → bundled .claude/
- `erk/data/github/` → bundled .github/

Configured in pyproject.toml via force-include.

## Sync Functions

- `sync_artifacts()` - Main sync, copies all bundled artifacts
- `sync_workflows()` - Sync BUNDLED_WORKFLOWS
- `sync_actions()` - Sync BUNDLED_ACTIONS

## Health Checks

- `find_orphaned_artifacts()` - Files in project not in bundle
- `find_missing_artifacts()` - Files in bundle not in project
- `get_artifact_health()` - Per-artifact status comparison
