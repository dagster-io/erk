---
title: Unified Dispatch Pattern
read_when:
  - "adding a new workflow to erk launch"
  - "modifying launch_cmd.py dispatch logic"
  - "understanding how local and remote dispatch are unified"
tripwires:
  - action: "creating separate local and remote dispatch functions for a workflow"
    warning: "Use the unified handler pattern — single RemoteGitHub-based handler for both local and remote. See unified-dispatch-pattern.md."
  - action: "adding a new workflow handler to launch_cmd.py"
    warning: "Follow the existing handler signature: (remote, *, owner, repo_name, ...) -> tuple[str, str]. See unified-dispatch-pattern.md."
---

# Unified Dispatch Pattern

All `erk launch` workflows use a single RemoteGitHub-based handler for both local and remote operation, eliminating separate local/remote code paths.

## Source

`src/erk/cli/commands/launch_cmd.py`

## Architecture

### Before: Dual Code Paths

Previously, each workflow had separate `_launch_local()` and `_launch_remote()` functions that used different gateway interfaces (local `gh` CLI vs REST API). This doubled the code and testing surface.

### After: Unified Handlers

Each workflow has a single handler that takes `RemoteGitHub` plus explicit parameters:

```python
def _dispatch_pr_rebase(
    remote: RemoteGitHub,
    *,
    owner: str,
    repo_name: str,
    pr_number: int,
    no_squash: bool,
    plan_id: str | None,
    model: str | None,
    ref: str,
) -> tuple[str, str]:
    """Returns (branch_name, run_id)."""
```

### Handler Return Convention

PR-targeting handlers return `tuple[str, str]` — `(branch_name, run_id)` — to enable post-dispatch enrichment. Non-PR handlers (like `learn`) return `None`.

### Entry Point Flow

The `launch` Click command:

1. Gets `RemoteGitHub` via `get_remote_github(ctx)`
2. Checks authentication via `remote.check_auth_status()`
3. Resolves `repo_id` via `@resolved_repo_option` decorator
4. Resolves dispatch ref (local config > `--ref` > `--ref-current` > default branch)
5. Applies local enrichments when available (PR inference from branch, plan ID resolution)
6. Dispatches to the appropriate unified handler
7. Calls `maybe_update_plan_dispatch_metadata()` for post-dispatch metadata updates

### Unified Handlers

| Handler                             | Workflow                  | Returns                 |
| ----------------------------------- | ------------------------- | ----------------------- |
| `_dispatch_pr_rebase`               | `pr-rebase`               | `(branch_name, run_id)` |
| `_dispatch_pr_address`              | `pr-address`              | `(branch_name, run_id)` |
| `_dispatch_pr_rewrite`              | `pr-rewrite`              | `(branch_name, run_id)` |
| `_dispatch_one_shot`                | `one-shot`                | `(branch_name, run_id)` |
| `_dispatch_learn`                   | `learn`                   | `None`                  |
| `_dispatch_consolidate_learn_plans` | `consolidate-learn-plans` | `None`                  |

### Post-Dispatch Enrichment

When a local repo is available and the handler returns `(branch_name, run_id)`, the entry point calls `maybe_update_plan_dispatch_metadata(ctx, repo, branch_name, run_id)` to update plan metadata with the dispatch run ID.

## Local Enrichments

When `has_local_repo` is `True`, the launch command provides additional features:

- **PR inference**: For `pr-rebase` without `--pr`, infers PR number from current branch
- **Plan ID resolution**: Resolves plan ID for the inferred branch via `plan_backend`
- **Dispatch ref from config**: Uses `ctx.local_config.dispatch_ref` as default

These enrichments are unavailable in remote-only mode (when using `--repo`).

## Related Documentation

- [Repo Resolution Pattern](../cli/repo-resolution-pattern.md) — `@resolved_repo_option` and `get_remote_github()`
- [Ref Resolution Patterns](../cli/ref-resolution-patterns.md) — dispatch ref resolution
- [RemoteGitHub Gateway](remote-github-gateway.md) — the gateway all handlers use
