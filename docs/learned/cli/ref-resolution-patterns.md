---
title: Ref Resolution Patterns
read_when:
  - "adding --ref or --ref-current to a CLI command"
  - "working with dispatch ref resolution"
  - "understanding how workflow dispatch ref is determined"
tripwires:
  - action: "implementing --ref and --ref-current handling manually in a command"
    warning: "Use resolve_dispatch_ref() from ref_resolution.py. It handles mutual exclusivity, config fallback, and detached HEAD validation."
  - action: "using --ref-current in remote mode (--repo)"
    warning: "--ref-current requires a local git repository. The launch command validates this and raises UsageError in remote mode."
---

# Ref Resolution Patterns

How `erk launch` and other dispatch commands determine which branch to dispatch a workflow from.

## Source

`src/erk/cli/commands/ref_resolution.py`

## `resolve_dispatch_ref(ctx, *, dispatch_ref, ref_current)`

Centralized resolver for `--ref` and `--ref-current` flags:

1. **Mutual exclusivity**: Raises `UsageError` if both `--ref` and `--ref-current` are provided
2. **`--ref-current`**: Gets current branch via `ctx.git.branch.get_current_branch()`. Raises `UsageError` on detached HEAD
3. **`--ref`**: Uses the provided value directly
4. **Fallback**: Returns `ctx.local_config.dispatch_ref` (user-configured default ref)

Returns `str | None` — `None` means "use caller's default" (typically the remote's default branch).

## Resolution Chain in `launch_cmd.py`

The full resolution chain for determining dispatch ref:

```
--ref flag (explicit)
  → --ref-current (current branch)
    → ctx.local_config.dispatch_ref (config default)
      → remote.get_default_branch_name() (API fallback)
```

### `--ref-current` Guard

When using `--repo` (remote mode), `--ref-current` is invalid because there is no local git repository to read the current branch from. The launch command validates:

```python
if ref_current and not has_local_repo:
    raise click.UsageError("--ref-current requires a local git repository")
```

### Default Branch Fallback

When all local resolution methods return `None`, the launch command queries the remote:

```python
if ref is None:
    ref = remote.get_default_branch_name(owner=repo_id.owner, repo=repo_id.repo)
```

## Usage

Commands that dispatch workflows should use `resolve_dispatch_ref()` for the local resolution step, then apply their own fallback for the remote case:

```python
ref = resolve_dispatch_ref(ctx, dispatch_ref=dispatch_ref, ref_current=ref_current)
if ref is None:
    ref = remote.get_default_branch_name(owner=owner, repo=repo)
```

## Related Documentation

- [Unified Dispatch Pattern](../architecture/unified-dispatch-pattern.md) — how dispatch handlers use the resolved ref
- [Repo Resolution Pattern](repo-resolution-pattern.md) — `@resolved_repo_option` for --repo handling
