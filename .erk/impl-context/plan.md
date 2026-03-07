# Prevent False Positive Default-Parameter Flags on Test Files

## Context
PR #8916 got 3 false positive review comments flagging default parameter values in test helper functions (`_make_fake_remote`, `_make_issue`, `_build_remote_context`). The `dignified-python` skill exempts test helpers, but this exemption has two gaps:
1. The review prompt (`.erk/reviews/dignified-python.md`) doesn't mention the exemption in its exceptions list
2. The exemption in `api-design.md` is scoped only to `tests/test_utils/`, but test helpers exist in regular test files too

## Changes

### 1. `.erk/reviews/dignified-python.md` — Add test helper exemption to Step 3 exceptions (line ~85)

Add a new bullet to the exceptions list (after the import alias exception):
```
- **No default parameters rule**: Does NOT apply to test helper functions (private `_` prefixed functions in test files like `test_*.py`) or Fake classes used for testing. These exist to reduce test boilerplate and defaults are their intended purpose.
```

### 2. `.claude/skills/dignified-python/references/api-design.md` — Broaden exemption wording (line 61)

Change from:
> Functions in `tests/test_utils/` that exist to reduce test boilerplate are explicitly exempt.

To:
> Test helper functions (private `_`-prefixed functions in test files, and functions in `tests/test_utils/`) that exist to reduce test boilerplate are explicitly exempt.

This covers both `tests/test_utils/` utility functions AND private helpers within individual test files.

## Verification
- Run `/local:review` or `/local:code-review` on a branch with test helper defaults to confirm no false positives
- Check that production code defaults are still flagged correctly
