# Fix Stale Documentation in plan-review Command

## Context

The `/erk:plan-review` command displays "coming in Phase 2" next to the `/erk:pr-address` step, but Plan Review Mode is fully implemented as documented in `docs/learned/erk/pr-address-workflows.md`.

## Change

**File:** `.claude/commands/erk/plan-review.md`

**Line 113:** Remove "(coming in Phase 2)" from the next steps output:

```diff
-3. Address feedback: /erk:pr-address (coming in Phase 2)
+3. Address feedback: /erk:pr-address
```

## Verification

Read the file after editing to confirm the change.