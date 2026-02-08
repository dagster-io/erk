---
title: Consolidation Labels
read_when:
  - "consolidating multiple learn plans"
  - "working with erk-consolidated label"
  - "preventing re-consolidation of issues"
  - "modifying /local:replan-learn-plans or /erk:replan consolidation behavior"
tripwires:
  - action: "consolidating issues that already have erk-consolidated label"
    warning: "Filter out erk-consolidated issues before consolidation. These are outputs of previous consolidation and should not be re-consolidated."
  - action: "adding erk-consolidated label to a single-issue replan"
    warning: "Only multi-plan consolidation gets the erk-consolidated label. Single-issue replans are updates, not consolidations."
---

# Consolidation Labels

## Why This Exists

Learn plan consolidation has a circular reference problem: `/local:replan-learn-plans` queries all open `erk-learn` issues and merges them into a single new issue — which itself carries the `erk-learn` label. Without protection, the next consolidation run would pick up its own output, creating an infinite loop of consolidation.

The `erk-consolidated` label breaks this cycle. It acts as a "already processed" marker: the consolidation query fetches `erk-learn` issues, then filters out any that also carry `erk-consolidated`.

## The Single-vs-Multi Decision

The label is **only** applied during multi-plan consolidation, never during single-plan replans. This distinction matters because:

- **Multi-plan consolidation** creates a new issue that _replaces_ multiple source issues. It must not be re-consolidated because it already represents a merge.
- **Single-plan replan** creates a new issue that _supersedes_ one source issue. It's a fresh plan against current codebase state and should remain eligible for future consolidation with other plans.

<!-- Source: .claude/commands/erk/replan.md, Step 7 item 4 -->

The label application happens in Step 7 of `/erk:replan`, after the new plan issue is created via `/erk:plan-save`.

<!-- Source: .claude/commands/local/replan-learn-plans.md, Step 1b -->

The filtering happens early in `/local:replan-learn-plans` (Step 1b) to avoid wasting API calls investigating issues that will be skipped.

## Label Lifecycle

An issue accumulates labels through its lifecycle — `erk-consolidated` is additive, not a replacement:

1. `/erk:learn` creates issue → labeled `erk-learn`
2. `/local:replan-learn-plans` consolidates N issues → new issue labeled `erk-learn` + `erk-consolidated`
3. Original N issues are closed with a cross-reference comment
4. Future consolidation runs skip the `erk-consolidated` issue automatically

## Edge Case: All Issues Already Consolidated

When `/local:replan-learn-plans` finds open `erk-learn` issues but every one has `erk-consolidated`, it reports this state and stops — there's nothing new to consolidate. This is a normal steady-state condition after a consolidation has run and no new learn plans have been created since.

## Related Documentation

- [Plan Lifecycle](lifecycle.md) — overall plan state management
- [Learn Workflow](learn-workflow.md) — how learn plans are created
- [Glossary: erk-consolidated](../glossary.md#erk-consolidated) — label definition
