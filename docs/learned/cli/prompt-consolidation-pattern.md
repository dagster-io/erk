---
title: Prompt Consolidation Pattern
read_when:
  - "implementing interactive prompts"
  - "consolidating multiple yes/no prompts"
  - "working with ctx.console.confirm"
  - "testing commands with user prompts"
tripwires:
  - action: "adding sequential yes/no prompts for a single decision"
    warning: "Consolidate into one binary choice. Multiple prompts for the same decision create unnecessary cognitive load. See the branch reuse example."
  - action: "testing prompts without matching confirm_responses array length"
    warning: "confirm_responses array length must match the number of prompts. Too few causes IndexError; too many indicates a prompt was removed without updating tests."
---

# Prompt Consolidation Pattern

Pattern for consolidating N sequential yes/no prompts into one binary choice. Reduces cognitive load and simplifies testing.

## Problem

Multiple sequential prompts for what is essentially a single decision:

```
Found existing branch P123-feature-01-23-0909.
Use existing branch? [Y/n]   # prompt 1
Delete old branches? [Y/n]    # prompt 2
```

This creates decision fatigue and makes testing more complex (each prompt needs a separate response).

## Solution

Consolidate into a single binary choice with clear consequences:

```
Found existing local branch(es) for this issue:
  - P123-feature-01-23-0909

New branch would be: P123-feature-02-15-1600

Reuse existing branch 'P123-feature-01-23-0909'?
If not, a new branch and PR will be created (old draft PR will be closed) [Y/n]
```

## Implementation

From `src/erk/cli/commands/submit.py`:

See `_prompt_existing_branch_action()` in
[`src/erk/cli/commands/submit.py`](../../../src/erk/cli/commands/submit.py)
for the full implementation. Key elements:

- `--force` mode: deletes old branches, returns `None` (create new)
- Normal mode: displays context, asks single binary prompt with consequences
- Returns branch name (reuse) or `None` (create new)

## Testing

From `tests/commands/submit/test_existing_branch_detection.py`:

See `test_submit_uses_existing_branch_when_user_confirms` in
[`tests/commands/submit/test_existing_branch_detection.py`](../../../tests/commands/submit/test_existing_branch_detection.py)
for the full test. The key elements:

- `setup_submit_context()` with `confirm_responses=[True]` matching the single prompt
- Asserts `exit_code == 0` and no new branches created (reused existing)

Key testing rules:

1. `confirm_responses` array length must match prompt count
2. `--force` mode bypasses all prompts (test separately with no `confirm_responses`)
3. Test both `True` and `False` paths

## Pattern Checklist

When implementing interactive prompts:

1. **Display context first** — show the user what they're deciding about
2. **Single binary prompt** — one question, not a sequence
3. **Include consequences** — explain what happens for each choice
4. **Default value** — set to the most common/safe option
5. **Force mode bypass** — `--force` flag skips all prompts for automation
6. **Return value encodes decision** — caller doesn't need to interpret prompt details

## Related Documentation

- [Erk Test Reference](../testing/testing.md) - General test patterns
