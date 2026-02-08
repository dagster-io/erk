---
title: Context Preservation in Replan Workflow
read_when:
  - "implementing or modifying replan workflow steps"
  - "debugging why a replanned issue produced a sparse plan"
  - "adding new plan-creation workflows that use EnterPlanMode"
tripwires:
  - action: "entering Plan Mode in replan or consolidation workflow"
    warning: "Gather investigation context FIRST (Step 6a). Enter plan mode only after collecting file paths, evidence, and discoveries. Sparse plans are destructive to downstream implementation."
---

# Context Preservation in Replan Workflow

Why the replan workflow has an explicit checkpoint (Steps 6a-6b) between investigation and plan creation, and why skipping it produces plans that waste downstream implementation effort.

## The Sparse Plan Problem

When the replan workflow investigates the codebase (Steps 4-5), the agent accumulates discoveries: file paths, completion percentages, corrections to the original plan, actual function names. These findings exist in conversation history — but conversation history is unstructured. If the agent enters Plan Mode directly after investigation, it writes the plan from memory, producing **sparse plans**: steps like "update gateway documentation" instead of "update `docs/learned/architecture/gateway-inventory.md` lines 45-67 to add CommandExecutor entry."

Sparse plans fail downstream because the implementing agent — running in a separate session with no access to the investigation context — must repeat the entire discovery process. This wastes 10-30K tokens on re-investigation and risks divergent conclusions since a different agent searching the codebase may find different things or make different choices.

### Root Cause

The failure mode is specifically about the **transition from investigation to plan creation**. The agent has the information but doesn't structure it before entering Plan Mode. Plan Mode starts a fresh planning context, and unstructured findings from earlier in the conversation get summarized into generic placeholders.

## The Two-Phase Checkpoint

<!-- Source: .claude/commands/erk/replan.md, Step 6a and Step 6b -->

The fix is architectural: Steps 6a and 6b in the replan command create an explicit checkpoint between investigation and plan creation.

**Step 6a (Gather):** Before calling `EnterPlanMode`, the agent explicitly collects and structures all investigation findings into four categories: investigation status per plan, specific discoveries (file paths, line numbers, commits), corrections to original plans, and verified codebase evidence (actual function names, class signatures, config values).

**Step 6b (Plan with context):** Only after structuring findings does the agent enter Plan Mode, with an explicit requirement that every implementation step includes specific file paths, concrete change descriptions, evidence citations, and testable verification criteria.

See Steps 6a-6b in `.claude/commands/erk/replan.md` for the canonical implementation.

### Why a Checkpoint, Not Just Better Prompting

The initial approach was to ask agents to "include investigation findings in the plan." This didn't work — without an explicit structuring step, agents summarize at too high a level. The checkpoint forces materialization: findings must be written out as structured data before Plan Mode begins, making them impossible to lose.

## Consolidation Amplifies the Problem

When consolidating multiple plans (`/erk:replan 123 456 789`), the sparse plan problem compounds:

- **Multiple investigation threads**: Each plan has its own status, corrections, and discoveries
- **Overlap analysis required**: Items appearing in multiple plans must be identified and merged
- **Attribution tracking**: The consolidated plan must record which source plan contributed each item

Without the 6a checkpoint, consolidation produces plans where overlap decisions are invisible, source attribution is lost, and the implementing agent has no idea why items were merged or kept separate.

## Downstream Economics

| Aspect | Sparse plan | Comprehensive plan |
|---|---|---|
| Implementation prep | Re-discover everything (10-30K tokens) | Execute immediately |
| Risk of divergence | High — different agent, new search results | Low — evidence constrains choices |
| Verification | Subjective ("looks done") | Objective (grep for specific values) |
| Consolidation attribution | Lost | Preserved per source plan |

## Applying to New Workflows

Any workflow that creates plans via `EnterPlanMode` should follow the same two-phase pattern. The key design principle: **never enter Plan Mode with unstructured findings in conversation history**. Always add an explicit gathering step that materializes findings into structured data before plan creation begins.

For prompt patterns and adaptation guidelines, see [Context Preservation Prompting](context-preservation-prompting.md).

---

## Related Documentation

- [Context Preservation Patterns](context-preservation-patterns.md) — anti-pattern vs. correct pattern examples with side-by-side comparisons
- [Context Preservation Prompting](context-preservation-prompting.md) — prompt structures for eliciting context in new workflows
- [Investigation Findings Checklist](../checklists/investigation-findings.md) — pre-Plan-Mode verification checklist
- [Replan Command](../../../.claude/commands/erk/replan.md) — canonical workflow with Steps 6a-6b
