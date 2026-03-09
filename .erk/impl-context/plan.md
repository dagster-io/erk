# Plan: Fix dignified-code-simplifier false positive on dict-value ternaries

## Context

The `dignified-code-simplifier` review bot (running on `claude-haiku-4-5`) is incorrectly flagging simple single-level ternaries used as dict values — e.g. `"squash": "false" if no_squash else "true"`. The SKILL.md already says these should NOT be flagged (line 32), but its examples only show assignment-style ternaries (`x = a if cond else b`). Haiku doesn't generalize from those examples to dict/list value contexts, so it produces false positives.

## Change

**File**: `.claude/skills/dignified-code-simplifier/SKILL.md` (line 32)

Add dict-value and list-element ternary examples to the existing "do NOT suggest replacing" bullet. Change from:

```
Examples: `slug = branch_slug if branch_slug else fallback()`, `x = a if condition else b`, `root = obj.primary if obj.primary else obj.fallback`
```

To:

```
Examples: `slug = branch_slug if branch_slug else fallback()`, `x = a if condition else b`, `root = obj.primary if obj.primary else obj.fallback`, `{"key": val_a if condition else val_b}`, `[x if x else default for x in items]`
```

This adds two examples showing ternaries inside dict literals and list comprehensions — the exact contexts where Haiku is producing false positives.

## Verification

1. Read the modified SKILL.md and confirm the examples list is correct
2. Run `/local:py-fast-ci` to ensure no lint/format/type issues
