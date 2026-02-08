---
title: Workflow Reliability Patterns
read_when:
  - deciding whether an operation should be agent-driven or workflow-native
  - designing multi-layer resilience for critical automated operations
  - ordering git operations that mix cleanup with reset in CI workflows
tripwires:
  - action: "relying on agent instructions as the sole enforcement for a critical operation"
    warning: "Agent behavior is non-deterministic. Critical operations need a deterministic workflow step as the final safety net."
  - action: "staging git changes (git add/git rm) without an immediate commit before a git reset --hard"
    warning: "git reset --hard silently discards staged changes. Commit and push cleanup BEFORE any reset step."
last_audited: "2026-02-08"
audit_result: regenerated
---

# Workflow Reliability Patterns

Erk's automated workflows blend AI agent behavior (non-deterministic) with scripted CI steps (deterministic). This document captures the cross-cutting principles for deciding which operations belong in which layer, and how to compose layers so critical operations never silently fail.

## The Core Distinction: Deterministic vs Non-Deterministic

Every operation in an automated workflow falls on a reliability spectrum. The key architectural decision is matching operation criticality to the right reliability tier.

| Operation type    | Reliability | Failure mode                               | Use for                                       |
| ----------------- | ----------- | ------------------------------------------ | --------------------------------------------- |
| Deterministic     | High        | Only fails if the step itself doesn't run  | Cleanup, state mutations, security-sensitive  |
| Non-deterministic | Low         | Context limits, misinterpretation, skipped | Creative/generative tasks, contextual choices |

**Why this matters:** Agent instructions feel reliable because they usually work. But "usually" is insufficient for operations that silently corrupt state when skipped. The `.worker-impl/` cleanup saga (below) demonstrates this concretely.

## Multi-Layer Resilience

For any operation where silent failure creates downstream problems, implement multiple independent layers. Each layer has distinct failure modes, so a single root cause can't defeat all layers simultaneously.

### The Reliability Hierarchy

| Layer                            | Failure mode                             | Appropriate for              |
| -------------------------------- | ---------------------------------------- | ---------------------------- |
| Agent instruction                | Context limits, misinterpretation        | Optimization, not guarantees |
| Staged git changes (uncommitted) | Silently discarded by `git reset --hard` | Nothing critical             |
| Dedicated workflow commit step   | Only fails if step condition is wrong    | Critical operations          |

**Key insight:** Only the dedicated workflow step is truly reliable. Upstream layers reduce the frequency of Layer 3 needing to act, but they cannot replace it. This mirrors the broader [defense-in-depth enforcement](../architecture/defense-in-depth-enforcement.md) pattern.

### Case Study: `.worker-impl/` Cleanup

This pattern was learned through production failures. The plan-implement workflow needed to remove `.worker-impl/` after implementation. Three approaches were tried, in order of discovery:

1. **Agent instruction** in the plan-implement command told Claude to `git rm -rf .worker-impl/`. Failed when agents hit context limits or misinterpreted the instruction.
2. **Staged deletion** via `git rm` in a workflow step, with commit happening later. Failed silently when a downstream `git reset --hard` discarded the staged changes.
3. **Dedicated commit-and-push step** that removes, commits, and pushes in one atomic operation. This is the only approach that reliably works.

<!-- Source: .github/workflows/plan-implement.yml, Clean up .worker-impl/ after implementation -->

See the "Clean up .worker-impl/ after implementation" step in `.github/workflows/plan-implement.yml` for the production implementation of Layer 3.

## Decision Framework

When adding an automated operation to a workflow:

| Question                           | If Yes                                            | If No                         |
| ---------------------------------- | ------------------------------------------------- | ----------------------------- |
| Does silent failure corrupt state? | Must be deterministic (workflow-native)           | Agent-dependent is acceptable |
| Can partial failure be detected?   | Agent-dependent with retry may work               | Must be workflow-native       |
| Does the operation need judgment?  | Agent-dependent, but add workflow-native fallback | Prefer workflow-native        |
| Is this followed by `git reset`?   | Commit and push BEFORE the reset                  | Standard ordering is fine     |

## The Commit-Before-Reset Rule

`git reset --hard` silently discards all staged-but-uncommitted changes. This is git's intended behavior, but in multi-step workflows it creates a subtle trap: a cleanup step that stages changes looks correct in isolation, but a later reset step silently undoes it.

**The rule:** Any cleanup that uses `git rm` or `git add` must commit and push _before_ any step that might run `git reset --hard`.

<!-- Source: .github/workflows/plan-implement.yml, Clean up .worker-impl/ after implementation -->
<!-- Source: .github/workflows/plan-implement.yml, Trigger CI workflows -->

See the step ordering in `.github/workflows/plan-implement.yml`: the cleanup step (commit + push) runs before the "Trigger CI workflows" step (which does `git reset --hard`). This ordering is load-bearing — reversing these steps silently drops the cleanup.

For the detailed anti-pattern with examples, see [plan-implement-workflow-patterns.md](../ci/plan-implement-workflow-patterns.md).

## Verification After Critical Operations

Don't assume a critical operation succeeded. Add an explicit verification step that fails loudly if the expected postcondition doesn't hold. This catches edge cases where the operation ran but didn't achieve its goal (e.g., `git rm` succeeded but the directory was recreated by a subsequent step).

<!-- Source: .github/actions/check-worker-impl/action.yml -->

See `.github/actions/check-worker-impl/action.yml` for an example: the composite action checks whether `.worker-impl/` exists and exposes a `skip` output, allowing downstream steps to react to unexpected state.

## Related Documentation

- [Defense-in-Depth Enforcement](../architecture/defense-in-depth-enforcement.md) — The broader pattern of multi-layer enforcement with reliability hierarchy
- [Plan Implement Workflow Patterns](../ci/plan-implement-workflow-patterns.md) — Specific cleanup-before-reset patterns in the plan-implement workflow
- [Worktree Cleanup](worktree-cleanup.md) — When and how `.worker-impl/` is cleaned up
- [Composite Action Patterns](../ci/composite-action-patterns.md) — Reusable GitHub Actions setup patterns
