---
title: False Positive Detection in Automated Reviews
description: Workflow for identifying and handling automated reviewer false positives
read_when:
  - handling automated review bot comments
  - dignified-code-simplifier or linter flags code
  - review comment references code already changed in PR
tripwires:
  - action: "making code changes based on automated review bot comments"
    warning: "Read full function context to verify it's not a false positive. Check if fix is already in PR or if pattern is intentional (test factories)."
last_audited: "2026-02-16 00:00 PT"
audit_result: clean
---

# False Positive Detection in Automated Reviews

## Overview

Automated review bots (dignified-code-simplifier, linters) may flag code patterns that are either already fixed in the PR or intentionally designed that way (e.g., test factory functions).

## Detection Workflow

1. **Read the flagged code** at its current state in the PR
2. **Check the PR diff** using `gh pr diff` to see what changes the PR already makes
3. **Verify the complaint is valid** - does the issue exist in current state?
4. **Check context** - is this a test factory function where defaults are intentional?
5. **If false positive**: Resolve thread with explanation, no code change needed

## Common False Positive Patterns

### Already Fixed in PR

The bot may reference a diff line number where the fix already exists. The bot flagged its own fix.

**Resolution**: Resolve thread explaining the issue is already addressed in the PR's changes.

### Test Factory Functions

Functions named `make_*` or `create_*` in test code are designed with defaults for ergonomic test creation. The "no default parameters" rule applies to production code, not test factories.

<!-- Source: tests/unit/tui/providers/test_provider.py, make_plan_row -->

See `make_plan_row()` in `tests/unit/tui/providers/test_provider.py` for an example - five parameters use defaults by design.

**Resolution**: Resolve as false positive, citing that test factory functions are exempt.
