---
title: External Docs Path Configuration
read_when:
  - "configuring docs path in .erk/config.local.toml"
  - "adding new configurable paths to the config system"
tripwires:
  - action: "setting docs.path at global config level"
    warning: "docs_path is REPO_ONLY in RepoConfigSchema. Per-user paths go in .erk/config.local.toml (gitignored)."
---

# External Docs Path Configuration

## Feature

The `[docs] path` setting in `.erk/config.local.toml` points erk docs commands to an external repository instead of the current project root.

## Configuration

```toml
# .erk/config.local.toml (gitignored, per-user)
[docs]
path = "/path/to/external/docs-repo"
```

## Schema

- Field: `docs_path: str | None` on `LoadedConfig`
- Config level: `REPO_ONLY` in `RepoConfigSchema` (not available at global level)
- Merge precedence: local config overrides repo config; `None` defaults to repo_root

## Resolver

<!-- Source: src/erk/agent_docs/operations.py, resolve_docs_project_root -->

`resolve_docs_project_root()` in `src/erk/agent_docs/operations.py` resolves the effective docs root. It returns `repo_root` when `docs_path` is `None`, validates that the configured path exists (raising `ClickException` if not), and returns the resolved `Path`.

## Integration

All docs commands use the resolver:

- `erk docs sync`
- `erk docs validate`
- `erk docs check`

No changes to the `AgentDocs` ABC were needed -- the resolver sits at the CLI layer.
