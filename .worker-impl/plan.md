# Plan: Fix Learn Workflow CI Crash on User Prompt

## Problem

The `learn-async` GitHub Actions workflow fails with:
```
"only prompt commands are supported in streaming mode"
```

This happens because:
1. CI runs `claude --print --output-format stream-json` (non-interactive streaming mode)
2. Step 5 of `/erk:learn` says "**Ask for validation**: Confirm the documentation items to write"
3. In streaming mode, Claude cannot prompt for user input - there's no TTY

## Solution

Modify Step 5 in the learn skill to detect CI/streaming mode and skip user confirmation, proceeding directly to write documentation.

## Implementation

### File: `.claude/commands/erk/learn.md`

**Location:** Step 5 (lines 569-579)

**Current text:**
```markdown
### Step 5: Present Findings

Present the synthesized plan to the user. The PlanSynthesizer output already includes:

1. **Context section** - What was built and why docs matter
2. **Summary statistics** - Documentation items, contradictions, tripwires
3. **Documentation items** - Prioritized with draft content starters and source attribution ([Plan], [Impl], [PR #N])

**Ask for validation**: Confirm the documentation items to write. Note that files will be written directly (not saved as a plan for later).

If the user decides to skip (no valuable insights), proceed to Step 7.
```

**New text:**
```markdown
### Step 5: Present Findings

Present the synthesized plan to the user. The PlanSynthesizer output already includes:

1. **Context section** - What was built and why docs matter
2. **Summary statistics** - Documentation items, contradictions, tripwires
3. **Documentation items** - Prioritized with draft content starters and source attribution ([Plan], [Impl], [PR #N])

**CI Detection**: Check if running in CI/streaming mode by running:

```bash
[ -n "$CI" ] || [ -n "$GITHUB_ACTIONS" ] && echo "CI_MODE" || echo "INTERACTIVE"
```

**If CI mode (CI_MODE)**: Skip user confirmation. Auto-proceed to Step 6 to write all HIGH and MEDIUM priority documentation items. This is expected behavior - CI runs should complete without user interaction.

**If interactive mode (INTERACTIVE)**: Confirm the documentation items to write with the user. Note that files will be written directly (not saved as a plan for later). If the user decides to skip (no valuable insights), proceed to Step 7.
```

## Verification

1. Run locally in interactive mode - should still prompt for confirmation
2. Trigger `learn-async` workflow on a plan issue - should complete without the streaming mode error
3. Check that documentation files are created in the PR

## Files Modified

- `.claude/commands/erk/learn.md` - Step 5 update