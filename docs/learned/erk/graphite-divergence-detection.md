---
title: Graphite Divergence Detection
read_when:
  - "debugging remote divergence errors during erk pr submit"
  - "understanding the Graphite-first submit flow's pre-checks"
  - "resolving 'branch is behind remote' errors"
  - "using --force flag with erk pr submit"
tripwires:
  - action: "running gt commands without --no-interactive"
    warning: "All gt commands MUST use --no-interactive. Without it, gt may prompt for input and hang indefinitely."
  - action: "pushing to a branch that may have been updated remotely without checking for divergence"
    warning: "The Graphite-first flow pre-checks for divergence before gt submit. Check with branch_exists_on_remote -> fetch_branch -> is_branch_diverged_from_remote."
---

# Graphite Divergence Detection

The Graphite-first submit flow includes proactive divergence detection before running `gt submit`. This prevents cryptic failures when the remote branch has been updated by CI, another session, or a prior submission.

## Guard Chain

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py:200-230 -->

The `_graphite_first_flow()` function in `submit_pipeline.py` runs a four-step guard chain before `gt submit`:

```
branch_exists_on_remote() → fetch_branch() → is_branch_diverged_from_remote() → check behind > 0
```

1. **`branch_exists_on_remote()`**: Skip divergence check entirely for new branches (no remote to diverge from)
2. **`fetch_branch()`**: Fetch the remote branch so local git knows the remote state
3. **`is_branch_diverged_from_remote()`**: Returns a divergence object with `ahead` and `behind` counts
4. **Check `behind > 0`**: If the local branch is behind remote AND `effective_force` is `False`, return a `SubmitError` with `error_type="remote_diverged"`. Note: `effective_force = state.force or is_plan_impl`, so plan implementations (`state.issue_number is not None`) auto-force and never hit this guard — it only applies to non-plan `erk pr submit` invocations.

## Core vs Graphite-First Difference

| Aspect           | Core flow            | Graphite-first flow         |
| ---------------- | -------------------- | --------------------------- |
| Divergence check | None (auto-rebases)  | Pre-checks and blocks       |
| Push mechanism   | `git push`           | `gt submit`                 |
| On divergence    | Rebase automatically | Error with resolution steps |

The core flow can auto-rebase because it controls the push directly. The Graphite-first flow delegates pushing to `gt submit`, which may behave unpredictably with diverged branches, so it pre-checks and blocks.

## Resolution Steps

When divergence is detected, the error message suggests two options:

1. **`erk pr sync-divergence --dangerous`**: Fetch, rebase onto remote, resolve any conflicts
2. **`erk pr submit -f`**: Force push, overriding whatever is on remote

## Graphite Tracking Divergence After Setup

A separate divergence scenario occurs when Graphite's internal tracking gets out of sync (e.g., after branch setup or manual git operations). Resolution:

```bash
gt track --no-interactive && gt restack --no-interactive && git push --force-with-lease
```

The `--no-interactive` flag is required on all `gt` commands to prevent hanging on prompts.

## The --force Escape Hatch

When `state.force` is `True` (from `erk pr submit -f`), the divergence check is bypassed entirely. The guard chain still runs `fetch_branch()` but skips the error return when `behind > 0`. This allows force-pushing over remote changes when the user explicitly opts in.

## Related Topics

- [Draft PR Branch Sync](../planning/draft-pr-branch-sync.md) - Branch sync before implementation
- [Graphite Stack Troubleshooting](graphite-stack-troubleshooting.md) - General Graphite troubleshooting
- [Draft PR Handling — Troubleshooting](../pr-operations/draft-pr-handling.md#troubleshooting-common-failures) - Related failure modes
