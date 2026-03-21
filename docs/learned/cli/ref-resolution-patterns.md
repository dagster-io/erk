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

<!-- Source: src/erk/cli/commands/launch_cmd.py, launch -->

When a local repo is available, `launch()` calls `resolve_dispatch_ref()` to apply the priority rules above. Without a local repo, only the `--ref` flag applies (no config fallback). In both cases, if the resolved ref is `None`, a final fallback queries the default branch name via GitHub API using `remote.get_default_branch_name()`.

See `launch()` in `src/erk/cli/commands/launch_cmd.py` for the full implementation.

## Flags

Both flags are standard across dispatch commands:

<!-- Source: src/erk/cli/commands/launch_cmd.py, launch -->

- `--ref` (text): Branch name to dispatch workflow from. Overrides the configured `dispatch_ref` if provided.
- `--ref-current` (flag): Dispatch workflow from the current branch. Mutually exclusive with `--ref`.

See `launch()` in `src/erk/cli/commands/launch_cmd.py` for the Click option definitions.

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
