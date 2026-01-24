# Plan: Add Plan Context Phase to `erk pr submit`

## Summary

Add a dedicated phase for fetching plan context in `erk pr submit`, providing user-visible output that indicates when plan content is being incorporated into PR generation.

## Current Behavior

The plan context is fetched silently between Phase 2 and Phase 3 (lines 197-202 in `submit_cmd.py`):
- No user output indicates plan context is being fetched
- No indication that plan content will be incorporated into the PR description

## Proposed Changes

### File: `src/erk/cli/commands/pr/submit_cmd.py`

1. **Add Phase 3: Fetching plan context** (after diff extraction, before PR generation)
   - Print phase header: `"Phase 3: Fetching plan context"`
   - Show progress while fetching
   - When plan found: `"   Incorporating plan from issue #XXXX"`
   - When linked to objective: `"   Linked to Objective #YYYY: <title>"`
   - When no plan found: `"   No linked plan found (branch not from erk-plan issue)"`

2. **Renumber subsequent phases:**
   - Current Phase 3 (Generating PR description) → Phase 4
   - Current Phase 4 (Graphite enhancement) → Phase 5
   - Current Phase 5 (Updating PR metadata) → Phase 6

3. **Update docstring** to reflect 6-phase workflow

### Output Example (with plan)

```
Phase 3: Fetching plan context
   Incorporating plan from issue #5805
   Linked to Objective #5123: Improve PR workflow
```

### Output Example (no plan)

```
Phase 3: Fetching plan context
   No linked plan found
```

## Implementation Details

The change is localized to `submit_cmd.py` lines ~197-221. The plan context fetching logic stays the same, we're just adding user-facing output around it.

Key considerations:
- Keep the phase brief when no plan is found (don't clutter output)
- Use consistent styling (dim for progress, green for success info)
- Maintain graceful degradation (no errors if plan not found)

## Files to Modify

- `src/erk/cli/commands/pr/submit_cmd.py` - Main submit command (add phase, renumber)

## Verification

1. Run `erk pr submit` on a branch from an erk-plan issue → should show plan incorporation message
2. Run `erk pr submit` on a regular branch → should show "No linked plan found"
3. Run `erk pr submit --debug` → verify all phases display correctly