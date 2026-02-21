# Plan: Add objective validation rule to AGENTS.md

## Context

Issue #7709 was created by an agent that bypassed the `create_objective_issue()` pipeline entirely — it used `gh issue create` directly with raw markdown, producing an objective with no metadata blocks. This made it invisible to `erk dash` (no progress, no content display). The root cause: no rule tells agents they MUST validate objectives after creation.

`erk objective check <number>` already exists and catches exactly this failure — it validates metadata blocks, roadmap parsing, label presence, and format integrity. We just need to make it mandatory.

## Change

**File:** `AGENTS.md` (line ~27, after the existing CRITICAL rules)

Add a new CRITICAL rule:

```markdown
**CRITICAL: After creating an objective issue, ALWAYS run `erk objective check <number>` to validate it.** If validation fails, the objective's metadata is broken and `erk dash` will not display it correctly. Fix the issue before proceeding.
```

This goes in the "CRITICAL: Before Writing Any Code" section alongside the other behavioral trigger rules (lines 18-26).

## Verification

- Read AGENTS.md after the edit to confirm the rule is in the right section
- Grep for "objective check" to confirm the rule is findable
