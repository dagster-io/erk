# Fix inaccurate fallback claim in planning tripwires doc

## Context

The tripwires documentation at `docs/learned/planning/tripwires.md` line 69 incorrectly states that `read_plan_ref()` falls back to "legacy issue.json". The actual implementation in `packages/erk-shared/src/erk_shared/impl_folder.py:310-332` shows the function tries `plan-ref.json` first and falls back to `ref.json` — there is no `issue.json` fallback.

## Changes

### File: `docs/learned/planning/tripwires.md`

**Line 69** — Fix the inaccurate fallback filename:

**Before:**
```
read_plan_ref() tries plan-ref.json first, falls back to legacy issue.json.
```

**After:**
```
read_plan_ref() tries plan-ref.json first, falls back to ref.json.
```

This is the only change. The rest of the tripwire entry on line 69 is accurate.

## Files NOT changing

- `packages/erk-shared/src/erk_shared/impl_folder.py` — the source of truth; no code changes needed
- All other documentation files — unaffected
- No test files — this is a documentation-only fix

## Verification

1. Read `docs/learned/planning/tripwires.md` line 69 after editing to confirm the text now says "falls back to ref.json"
2. Cross-reference with `packages/erk-shared/src/erk_shared/impl_folder.py:323` which iterates `("plan-ref.json", "ref.json")`