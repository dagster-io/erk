# Plan: Delegate replan validation/metadata to subagent

## Context

When `/erk:replan` is called with N issues, Steps 2 and 2.5 run 2N bash calls in the main conversation context (N × `get-issue-body` + N × `get-plan-metadata`). For 8 issues, that's 16 bash calls with full JSON responses polluting the primary context window. These should be delegated to a single Task subagent that returns a compact structured summary.

## Changes

**File:** `.claude/commands/erk/replan.md`

### Edit 1: Replace Steps 2 and 2.5 (lines 35–81) with unified Step 2

Replace the current **Step 2: Validate All Plans** (lines 35–63) and **Step 2.5: Extract Objective Issue** (lines 65–81) with a single Step 2 that delegates to a `general-purpose` haiku Task agent.

The new Step 2 instructs the agent to:
1. Run `erk exec get-issue-body <number>` for each issue
2. Run `erk exec get-plan-metadata <number> objective_issue` for each issue
3. Return a structured summary with:
   - Header flags: `VALIDATION`, `CONSOLIDATION_MODE`, `IS_LEARN_PLAN`
   - Issues table: `# | Title | State | erk-plan | erk-learn | objective_issue`
   - `OBJECTIVE_STATUS`: `AGREED:<number>`, `AGREED:none`, or `CONFLICT`
   - `ERRORS` section (only if VALIDATION is FAIL)
   - `WARNINGS` section (only if closed issues found)

The main agent then:
- Aborts if VALIDATION is FAIL (same error messages as today)
- Displays warnings for closed issues
- Stores `IS_LEARN_PLAN`, `CONSOLIDATION_MODE`, titles, and resolved `objective_issue`
- If OBJECTIVE_STATUS is CONFLICT, asks user which objective to use

### Edit 2: Fix back-reference in Step 7 (line 366)

Change "Step 2.5" → "Step 2":
```
- **If consolidating with conflicting objectives**: Use the objective chosen by the user in Step 2
```

## Verification

1. Run `/local:replan-learn-plans` with multiple open erk-learn issues
2. Confirm: main context shows 1 Task call → compact summary (not 2N bash blobs)
3. Confirm: validation failures still abort with correct error messages
4. Confirm: IS_LEARN_PLAN, objective_issue, and titles are correctly propagated to Steps 6–7