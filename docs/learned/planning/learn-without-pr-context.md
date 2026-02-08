---
title: Learn Without PR Context
read_when:
  - debugging learn workflow failures where PR data is missing
  - implementing new learn pipeline steps that consume PR context
  - understanding why learn output lacks review feedback
tripwires:
  - action: "treating missing PR as an error in the learn pipeline"
    warning: "No-PR is a valid workflow state, not an error. The learn pipeline must degrade gracefully — sessions alone provide sufficient material for insight extraction."
  - action: "adding a new PR-dependent step to trigger-async-learn"
    warning: "Any new PR-dependent step must handle the None case from _get_pr_for_plan_direct. The entire PR comment block is gated on pr_result not being None."
---

# Learn Without PR Context

## Why This Matters

The learn pipeline extracts documentation insights from plan sessions. The richest input includes both session XML _and_ PR review comments (inline threads + discussion), but a PR doesn't always exist when learn runs. Plans may be in-progress, abandoned, consolidated into a different PR, or implemented for local testing only.

Treating missing PR context as an error would block learn from running in these valid scenarios. The pipeline is designed so that sessions alone — containing the planning rationale and implementation decisions — provide sufficient material for insight extraction. PR review comments are enrichment, not a prerequisite.

## Graceful Degradation Architecture

<!-- Source: src/erk/cli/commands/exec/scripts/trigger_async_learn.py, _get_pr_for_plan_direct -->

The `trigger-async-learn` orchestrator resolves the plan's PR through a chain of lookups: issue → metadata block → branch name → PR. Each step returns `None` on failure, and the entire PR comment-fetching block is gated on the result.

When `_get_pr_for_plan_direct` returns `None`, the orchestrator logs a warning and skips straight to gist upload. No review comments or discussion comments are written to the learn materials directory. The downstream learn agent receives only preprocessed session XML — which still contains all planning rationale, implementation decisions, and tool interactions.

When a PR _is_ found, the orchestrator fetches two separate comment types via gateway calls (not `gh` CLI):

| Comment type        | File written                  | Contains                                  |
| ------------------- | ----------------------------- | ----------------------------------------- |
| Review threads      | `pr-review-comments.json`     | Inline code review threads with file/line |
| Discussion comments | `pr-discussion-comments.json` | Top-level PR conversation                 |

Both use LBYL discriminated union checking (`isinstance(result, PRNotFound)`) rather than exception handling, consistent with erk's error patterns.

## Valid No-PR Scenarios

Not all plan implementations produce PRs:

- **Work in progress** — implementation isn't ready for review yet
- **Abandoned plans** — decided not to proceed after implementation
- **Consolidated work** — plan's changes merged into a different PR
- **Local testing** — no intent to merge (e.g., testing the learn workflow itself)

The learn pipeline must work identically in all cases. The quality difference is additive: PR comments enrich output but their absence doesn't degrade what sessions provide.

## Anti-Patterns

**Assuming PR always exists**: Any code in the learn pipeline that calls gateway PR methods without first checking `_get_pr_for_plan_direct` will crash on no-PR plans. The existing orchestrator gates all PR operations behind a single `None` check — new PR-dependent steps must live inside that same gate.

**Using `gh` CLI for PR detection in Python**: The orchestrator uses typed gateway calls with discriminated union returns, not subprocess calls to `gh`. This provides type safety and LBYL error handling. Don't mix the two approaches.

## Related Documentation

- [Async Learn Local Preprocessing](async-learn-local-preprocessing.md) — How session materials are prepared before gist upload
- [Learn Workflow](learn-workflow.md) — Complete async learn flow and agent tier architecture
