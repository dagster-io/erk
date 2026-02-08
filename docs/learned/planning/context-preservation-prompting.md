---
audit_result: edited
last_audited: '2026-02-08'
read_when:
- writing slash commands that create plans
- designing any workflow that calls EnterPlanMode
- understanding why plans lose investigation context
title: Context Preservation Prompting Patterns
tripwires:
- action: creating a new plan-generating command without a pre-plan gathering step
  warning: Without explicit context materialization before EnterPlanMode, agents produce
    sparse plans. Apply the two-phase pattern from this document.
- action: prompting an agent to 'include findings in the plan' without structuring
    them first
  warning: Unstructured prompts don't work — agents summarize at too high a level.
    Use the four-category gathering step instead.
---

# Context Preservation Prompting Patterns

How to structure prompts in plan-creating commands so that investigation findings survive the transition into Plan Mode, rather than being summarized away into generic placeholders.

## The Core Problem

Plan Mode starts a fresh planning context. When an agent has been investigating the codebase for thousands of tokens, entering Plan Mode creates a boundary — findings from the investigation phase get compressed into memory rather than carried forward as structured data. Without explicit prompting to materialize findings first, agents write "update the documentation" instead of "update `docs/learned/architecture/gateway-inventory.md` to add CommandExecutor entry."

This matters because the investigating agent and implementing agent are different sessions. The plan is the **only artifact** that crosses the boundary. See [Context Preservation in Replan](context-preservation-in-replan.md) for the full economics of this failure mode.

## The Two-Phase Prompt Pattern

<!-- Source: .claude/commands/erk/replan.md, Step 6a and Step 6b -->

Every plan-creating command needs two distinct phases in its prompt structure. The canonical implementation is Steps 6a-6b in `.claude/commands/erk/replan.md`.

**Phase 1 — Gather (before `EnterPlanMode`):** The command explicitly instructs the agent to collect and structure all investigation findings into categories before entering Plan Mode. This forces materialization — findings become structured data that can't be lost.

**Phase 2 — Plan (inside Plan Mode):** The command specifies that every implementation step must include specific file paths, concrete change descriptions, evidence citations, and testable verification criteria.

The critical design choice is that these are **separate, sequential steps** in the command. Combining them into a single "investigate and plan" instruction reliably produces sparse plans because agents shortcut the gathering phase.

## Why Specific Prompt Techniques Matter

Three prompt engineering lessons emerged from repeated failures in the replan workflow (issues #6139, #6167):

### 1. The CRITICAL Tag Forces Compliance

Agents frequently skip gathering steps that aren't marked as mandatory. Without the `CRITICAL` keyword on the gathering requirement, agents jump straight to `EnterPlanMode` after investigation. The replan command marks Step 6b's requirements with `**CRITICAL:**` for this reason.

### 2. Four Categories Prevent Selective Gathering

Asking agents to "gather findings" is too vague — they gather what seems important and drop the rest. Specifying exactly four categories to collect produces reliable results:

1. **Investigation status** — completion percentages, item-by-item status
2. **Specific discoveries** — file paths, line numbers, commit hashes, PR numbers
3. **Corrections** — what the original plan got wrong
4. **Codebase evidence** — actual function names, class signatures, config values

These four categories were chosen because each addresses a different failure mode in downstream implementation. See [Context Preservation Patterns](context-preservation-patterns.md) for the five dimensions that map to these categories.

### 3. Anti-Pattern Examples Anchor Expectations

Showing both a sparse plan step and a comprehensive one in the command prompt calibrates the agent's output level. Without the contrast, agents' default level of specificity is too abstract for execution by a separate agent.

## Adapting to New Workflows

| Workflow type                  | How to apply the pattern                                                                             |
| ------------------------------ | ---------------------------------------------------------------------------------------------------- |
| Replan (single plan)           | Full two-phase pattern with all four gathering categories                                            |
| Consolidation (multiple plans) | Two-phase pattern plus overlap analysis, merge decisions, and attribution tracking per source plan   |
| Fresh plan (no prior plan)     | Two-phase pattern with categories 2 and 4 (discoveries and evidence); categories 1 and 3 don't apply |
| Interview-first plan           | Three phases: interview → gather → plan (see below)                                                  |

### Interview Then Gather Then Plan

<!-- Source: .claude/commands/local/interview.md -->

When requirements are ambiguous, `/local:interview` gathers context through user questions before planning. This creates a three-phase flow:

1. **Interview** — `/local:interview` explores the codebase and asks clarifying questions. It uses `allowed-tools` frontmatter to enforce read-only behavior, making it safe within plan mode. See [Tool Restriction Safety](../commands/tool-restriction-safety.md) for the enforcement mechanism.
2. **Gather** — After the interview, the standard gathering step materializes both the interview findings and any codebase discoveries into structured data.
3. **Plan** — Enter Plan Mode with the structured context.

The key insight is that interview output alone is insufficient — it captures requirements but not codebase evidence. The gathering step bridges the gap by combining user requirements with verified technical details.

## Anti-Patterns

| Anti-pattern                                       | Why it fails                                                           | Correct approach                                             |
| -------------------------------------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------ |
| Single "investigate and plan" instruction          | Agent shortcuts gathering, enters Plan Mode with unstructured findings | Separate gather step before EnterPlanMode                    |
| "Include findings in the plan" without structuring | Agent summarizes at too high a level                                   | Specify four categories to collect                           |
| Gathering step without CRITICAL tag                | Agent skips it as optional                                             | Mark gathering requirements as CRITICAL                      |
| Only gathering file paths (no evidence)            | Implementing agent must re-verify everything                           | Gather all four categories including actual names and values |

---

## Related Documentation

- [Context Preservation in Replan](context-preservation-in-replan.md) — The sparse plan problem and why the two-phase checkpoint exists
- [Context Preservation Patterns](context-preservation-patterns.md) — Five dimensions of plan specificity with anti-pattern examples
- [Investigation Findings Checklist](../checklists/investigation-findings.md) — Pre-Plan-Mode verification checklist
- [Tool Restriction Safety](../commands/tool-restriction-safety.md) — How `allowed-tools` enables safe read-only commands in plan mode
