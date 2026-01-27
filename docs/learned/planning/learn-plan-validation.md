---
title: Learn Plan Validation
read_when:
  - "creating erk-learn plans"
  - "preventing learn plan cycles"
  - "validating learn workflow"
tripwires:
  - action: "creating erk-learn plan for an issue that already has erk-learn label"
    warning: "Validate target issue has erk-plan label, NOT erk-learn. Learn plans analyze implementation plans, not other learn plans (cycle prevention)."
---

# Learn Plan Validation

Validation rules for `erk learn` workflow to prevent invalid configurations and cycles.

## Core Rule: No Learn-on-Learn

**A learn plan MUST target an issue with `erk-plan` label, NOT `erk-learn` label.**

This prevents cycles where:
- Issue A (erk-learn) analyzes Issue B (erk-learn)
- Issue B analyzes Issue A
- Or longer cycles: A → B → C → A

## Validation Points

### 1. Issue Label Validation

When creating a learn plan (via `erk learn <issue>` or automatic trigger):

**Check:** Target issue has `erk-plan` label
**Error:** If target has `erk-learn` label, reject with error:

```
Error: Cannot create learn plan for issue #123
Reason: Target issue has 'erk-learn' label (should have 'erk-plan')
Learn plans analyze implementation plans, not other learn plans.
```

### 2. Implementation Origin Validation

When creating a learn plan for a PR:

**Check:** PR is linked to an issue with `erk-plan` label
**Error:** If linked issue has `erk-learn` label, reject:

```
Error: PR #456 is linked to issue #123 with 'erk-learn' label
Learn plans must target issues with 'erk-plan' label
```

### 3. Manual Override (Advanced)

For special cases (meta-analysis of learn workflow itself):

**Flag:** `--allow-learn-on-learn` (hidden flag)
**Use case:** Analyzing the learn workflow mechanism itself
**Warning:** Creates a meta-learn plan that won't be automatically processed

## Learn Workflow Stages

Understanding the labels helps prevent confusion:

| Label | Stage | Purpose |
|-------|-------|---------|
| `erk-plan` | Implementation plan | Work to be done (code changes) |
| `erk-learn` | Documentation plan | Documentation to be written (from completed work) |

**Flow:**
1. Create `erk-plan` issue → Implement code → Land PR → Mark plan as complete
2. Create `erk-learn` issue → Extract insights from session → Write docs → Mark learn complete

Learn plans look **backward** at completed work, not **forward** at future work.

## Implementation Location

Validation logic is in:

```
packages/erk/src/erk/learn/validation.py
```

**Function:** `validate_learn_target(issue_number: int, github: GitHub) -> ValidationResult`

**Called by:**
- `erk learn <issue>` command
- Automatic learn plan creation after PR land
- Learn plan queue processor

## Error Messages

### Cycle Prevention Error

```
Cannot create learn plan for issue #123: Target has 'erk-learn' label

Learn plans analyze implementation work (erk-plan issues), not other
learn plans (erk-learn issues).

If you need to document the learn workflow itself, use:
  erk learn --allow-learn-on-learn 123
```

### Missing Plan Label

```
Cannot create learn plan for issue #123: No 'erk-plan' label found

Learn plans require a completed implementation plan to analyze.

If issue #123 is closed and had an associated erk-plan issue, use that
issue number instead.
```

## Testing Validation

Unit tests should cover:

1. **Valid case:** Target has `erk-plan` label → success
2. **Invalid case:** Target has `erk-learn` label → error
3. **No label case:** Target has neither label → error
4. **Override case:** `--allow-learn-on-learn` flag → success with warning

Integration test:

```bash
# Should succeed
erk learn 123  # where #123 has erk-plan label

# Should fail
erk learn 456  # where #456 has erk-learn label
# Error: Cannot create learn plan for issue #456 (has 'erk-learn' label)
```

## Related Topics

- [Learn Workflow](../architecture/learn-workflow.md) - Complete learn process
- [Learn Origin Tracking](../architecture/learn-origin-tracking.md) - Linking plans to sessions
- [Parallel Agent Pattern](../architecture/parallel-agent-pattern.md) - Learn orchestration
