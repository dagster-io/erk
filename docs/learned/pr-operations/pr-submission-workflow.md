---
title: Git-Only PR Submission Path
read_when:
  - understanding why two separate git-only PR paths exist
  - working on the git-pr-push command or the core submit flow
  - debugging PR creation in environments without Graphite
  - deciding whether to use the command-level or pipeline-level git path
tripwires:
  - action: "adding git-only PR logic to a new location"
    warning: "Two git-only paths already exist (command-level and pipeline-level). Understand why both exist before adding a third. See pr-submission-workflow.md."
  - action: "using gh pr create directly in Python code"
    warning: "The pipeline uses ctx.github.create_pr() (REST API gateway), not gh pr create. The command-level path uses gh CLI directly because it runs in shell context. See pr-submission-workflow.md."
last_audited: "2026-02-08 00:00 PT"
audit_result: clean
---

# Git-Only PR Submission Path

Erk has **two distinct implementations** of git-only PR creation, serving different execution environments. Understanding why both exist — and when each applies — prevents agents from duplicating logic or using the wrong path.

## Why Two Paths Exist

The git-only submission path appears in two places because of a fundamental execution context split:

| Path               | Where it lives                           | Execution context         | Tool access                  |
| ------------------ | ---------------------------------------- | ------------------------- | ---------------------------- |
| **Command-level**  | `/erk:git-pr-push` Claude command        | Shell (Claude Code agent) | `git`, `gh`, `erk exec` CLIs |
| **Pipeline-level** | `_core_submit_flow()` in submit pipeline | Python (erk CLI)          | Gateway ABCs, typed results  |

<!-- Source: .claude/commands/erk/git-pr-push.md -->
<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, _core_submit_flow -->

**The command-level path** (`/erk:git-pr-push`) is a Claude Code command spec — it instructs the agent to run shell commands directly. It exists because remote agents (GitHub Actions, plan-submit) can't install Graphite and don't have `erk pr submit` available in all contexts. The agent orchestrates `git push`, `gh pr create`, and `erk exec` scripts sequentially.

**The pipeline-level path** (`_core_submit_flow()`) is the Python fallback within `erk pr submit` when Graphite is unavailable or `--no-graphite` is passed. It uses gateway abstractions (`ctx.github.create_pr()`, `ctx.git.remote.push_to_remote()`) and returns typed results (`SubmitState | SubmitError`).

**Why not consolidate?** The command-level path runs in a shell agent that can't call Python gateway methods. The pipeline-level path runs in Python and shouldn't shell out to `gh pr create` when a typed gateway exists. They share the same logical workflow but operate in incompatible execution models.

## Behavioral Differences Between the Two Paths

Despite doing "the same thing," the paths diverge in important ways:

| Behavior            | Command-level (git-pr-push)          | Pipeline-level (\_core_submit_flow)          |
| ------------------- | ------------------------------------ | -------------------------------------------- |
| PR creation API     | `gh pr create` CLI                   | `ctx.github.create_pr()` REST API            |
| Commit handling     | Preserves all commits                | Squashes via amend in finalize step          |
| Divergence handling | Suggests manual fix                  | Auto-rebases if behind, errors if diverged   |
| Existing PR check   | `gh pr list --head` shell query      | `ctx.github.get_pr_for_branch()` typed union |
| Footer generation   | `erk exec get-pr-body-footer` script | `build_pr_body_footer()` Python call         |
| Force push          | Never (suggests manual)              | Only with `-f` flag                          |

**Why the REST API difference matters:** The pipeline uses `gh api` (REST) instead of `gh pr create` (GraphQL) to preserve GitHub's GraphQL rate limit quota. The command-level path uses `gh pr create` because it's simpler for shell scripting and remote agents don't run enough operations to hit quotas.

## The BranchManager Abstraction

<!-- Source: packages/erk-shared/src/erk_shared/gateway/branch_manager/abc.py, BranchManager -->
<!-- Source: packages/erk-shared/src/erk_shared/gateway/branch_manager/git.py, GitBranchManager -->

Both Graphite and git-only paths share behavior through `BranchManager`, an ABC with two implementations. The git-only implementation (`GitBranchManager`) has important design decisions:

**Force push by default:** `GitBranchManager.submit_branch()` always uses `--force` for parity with Graphite's submit behavior (which force-pushes during quick iterations). This differs from the command-level path, which never force-pushes — because command-level runs are typically first-time submissions, while `BranchManager.submit_branch()` is called by quick-submit during iterative development.

**No-op methods:** Several `BranchManager` methods are no-ops in the git implementation (`track_branch`, `get_parent_branch`, `get_branch_stack`). These represent Graphite-only concepts. The no-ops are intentional — they let consumers call the interface uniformly without checking `is_graphite_managed()` first.

## Stacked PR Constraint in Core Flow

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, _core_submit_flow -->

The pipeline-level path includes a guard that blocks PR creation when the parent branch (from Graphite metadata) has no PR. This prevents creating a child PR with the wrong base — GitHub would target it against trunk instead of the parent branch, producing an unreviable diff.

**Why this only applies to the pipeline path:** The command-level path (`/erk:git-pr-push`) is designed for standalone PRs. It doesn't check parent branches because it's explicitly for non-stacked use cases. The pipeline path handles both stacked and standalone PRs, so it must guard against the stacked case.

## Anti-Patterns

**Merging the two paths into one:** The execution contexts are fundamentally different (shell agent vs Python process). Past attempts to unify them with a `--no-stack` flag failed because the behavioral differences are too numerous.

**Using the command-level path when `erk pr submit` is available:** The pipeline path provides auto-rebase, AI-generated descriptions, plan context integration, and Graphite fallback. The command-level path exists for environments where the CLI isn't available, not as a preferred alternative.

**Shelling out to `gh pr create` in Python code:** Use the typed GitHub gateway instead. The gateway returns `PRDetails | PRNotFound` for LBYL handling; parsing CLI output loses type safety. See [PR Creation Patterns](pr-creation-patterns.md).

## Related Documentation

- [PR Submission Decision Framework](../cli/pr-submission.md) — When to use `/erk:git-pr-push` vs `/erk:pr-submit`
- [PR Submit Pipeline Architecture](../cli/pr-submit-pipeline.md) — The 8-step pipeline design and dispatch logic
- [PR Creation Patterns](pr-creation-patterns.md) — LBYL check-before-create pattern used by both paths
- [Checkout Footer Syntax](checkout-footer-syntax.md) — Footer generation shared across both paths
