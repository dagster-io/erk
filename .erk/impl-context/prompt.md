Fix an inaccurate claim in `docs/learned/planning/tripwires.md` at line 69.

**File:** `docs/learned/planning/tripwires.md`, line 69

**Before:**
```
read_plan_ref() tries plan-ref.json first, falls back to legacy issue.json.
```

**After:**
```
read_plan_ref() tries plan-ref.json first, falls back to ref.json.
```

This is a one-line doc correction. The `legacy issue.json` fallback was removed from `read_plan_ref()` — the function now only tries `plan-ref.json` and `ref.json`. No tests needed. Verify the change visually by reading line 69 of the file after making the edit.
