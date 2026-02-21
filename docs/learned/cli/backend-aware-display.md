---
title: CLI Backend-Aware Display Patterns
read_when:
  - "adding CLI commands that behave differently for issue vs draft-PR plans"
  - "routing between gh issue and gh pr commands based on plan backend"
  - "understanding how plan_backend affects CLI output"
tripwires:
  - action: "using gh issue view on a plan without checking plan backend type"
    warning: "Draft-PR plan IDs are PR numbers, not issue numbers. Using gh issue view on a draft-PR plan produces a confusing 404. Route to gh pr view based on backend type."
    score: 7
---

# CLI Backend-Aware Display Patterns

CLI commands that interact with plans must handle two backends: `github` (issue-based) and `github-draft-pr` (draft PR-based). This document covers the patterns for routing behavior based on backend type.

## Three Detection Patterns

The codebase uses three approaches to detect the active backend, each suited to different contexts:

### Pattern 1: Interface Delegation (Preferred)

<!-- Source: src/erk/cli/commands/learn/learn_cmd.py -->

Commands that operate on plan metadata should use the `plan_backend` abstract interface without checking the type. Both backends implement the same methods:

```python
# learn_cmd.py — no backend branching needed
plan_id = ctx.plan_backend.resolve_plan_id_for_branch(ctx.cwd, branch_name)
sessions = ctx.plan_backend.find_sessions_for_plan(repo_root, plan_id)
value = ctx.plan_backend.get_metadata_field(repo_root, plan_id, "learn_materials_branch")
```

Use this when the operation is the same regardless of backend — the abstraction handles routing internally.

### Pattern 2: Provider Name Check (Exec Scripts)

<!-- Source: src/erk/cli/commands/exec/scripts/handle_no_changes.py:79 -->

Exec scripts that need different behavior use the provider name:

```python
backend = require_plan_backend(ctx)
is_draft_pr = backend.get_provider_name() == "github-draft-pr"
```

Use this in exec scripts where `require_plan_backend()` is already in scope.

### Pattern 3: Direct Comparison (TUI)

<!-- Source: src/erk/tui/commands/registry.py:31-33, _is_github_backend -->

The TUI command palette uses a simple predicate:

```python
def _is_github_backend(ctx: CommandContext) -> bool:
    return ctx.plan_backend == "github"
```

Use this for availability filtering where you need a boolean check.

## Terminology Routing

When displaying plan information to users, use backend-appropriate terminology:

| Concept      | Issue Backend   | Draft-PR Backend |
| ------------ | --------------- | ---------------- |
| Plan storage | "issue"         | "draft PR"       |
| Plan ID      | Issue number    | PR number        |
| View command | `gh issue view` | `gh pr view`     |
| Plan label   | `erk-plan`      | `erk-plan`       |

## When to Use Each Pattern

| Scenario                                        | Pattern              |
| ----------------------------------------------- | -------------------- |
| Metadata reads/writes                           | Interface delegation |
| Different GitHub CLI commands needed            | Provider name check  |
| Command visibility filtering                    | Direct comparison    |
| Output text differences ("issue" vs "draft PR") | Provider name check  |

## Related Topics

- [Backend-Aware TUI Commands](../tui/backend-aware-commands.md) — TUI-specific command filtering by backend
- [Draft PR Plan Backend](../planning/draft-pr-plan-backend.md) — Backend architecture and selection
