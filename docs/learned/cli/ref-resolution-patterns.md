---
title: Ref Resolution Patterns
read_when:
  - "adding --ref or --ref-current flags to a dispatch command"
  - "working with resolve_dispatch_ref"
  - "understanding dispatch ref fallback behavior"
tripwires:
  - action: "resolving --ref and --ref-current manually in a command handler"
    warning: "Use resolve_dispatch_ref() from ref_resolution.py. It handles mutual exclusivity, detached HEAD detection, and config fallback. See ref-resolution-patterns.md."
---

# Ref Resolution Patterns

`src/erk/cli/commands/ref_resolution.py` provides shared ref resolution for dispatch commands.

## `resolve_dispatch_ref(ctx, *, dispatch_ref, ref_current) -> str | None`

Resolves which branch to dispatch from, in priority order:

1. Mutual exclusivity check: `--ref` and `--ref-current` are mutually exclusive
2. `--ref-current`: returns `ctx.git.branch.get_current_branch(ctx.cwd)` (raises if detached HEAD)
3. `--ref` provided: returns the explicit ref string
4. Config fallback: returns `ctx.local_config.dispatch_ref` (may be `None`)

Returns `None` if no ref is configured — callers then fall through to default branch resolution.

## Full Ref Resolution in `launch` Command

The `launch` command implements the full resolution chain after calling `resolve_dispatch_ref()`:

```python
if has_local_repo:
    ref = resolve_dispatch_ref(ctx, dispatch_ref=dispatch_ref, ref_current=ref_current)
else:
    ref = dispatch_ref  # Only --ref flag applies without local repo

if ref is None:
    # Final fallback: query default branch name from GitHub API
    ref = remote.get_default_branch_name(owner=repo_id.owner, repo=repo_id.repo)
```

The final fallback calls `remote.get_default_branch_name()` — this is a GitHub REST API call.

## Flags

Both flags are standard across dispatch commands:

```python
@click.option("--ref", "dispatch_ref", type=str, default=None,
    help="Branch to dispatch workflow from (overrides config dispatch_ref)")
@click.option("--ref-current", is_flag=True, default=False,
    help="Dispatch workflow from the current branch")
```

## Remote Mode Behavior

Without a local repo (`--repo` flag used without local git):

- `--ref-current` is rejected with `click.UsageError`
- `--ref` is used directly
- Config dispatch_ref is unavailable (no local config)
- Falls back to GitHub API for default branch

## Source

`src/erk/cli/commands/ref_resolution.py` — used by `launch_cmd.py`, `dispatch_cmd.py`, and other dispatch-capable commands.

## Related Documentation

- [Unified Dispatch Pattern](../architecture/unified-dispatch-pattern.md) — full dispatch flow
- [Repo Resolution Pattern](repo-resolution-pattern.md) — `--repo` flag handling
