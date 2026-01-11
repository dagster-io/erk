# Plan: Update Docs/Comments for PR #4693 Changes

## Context

PR #4693 removed the `plan_type`, `source_plan_issues`, and `extraction_session_ids` metadata fields from the plan-header schema, replacing them with label-based classification using the `erk-learn` GitHub label.

**Key change:** Learn plans are now detected by checking for the `erk-learn` label on the GitHub issue, NOT by parsing `plan_type: learn` from metadata.

## Files Requiring Updates

### 1. `docs/learned/glossary.md` - Lines 854, 869-870

**Current (outdated):**
```markdown
- Marked with `plan_type: learn` in the plan-header metadata
...
- `erk plan submit` when the source issue has `plan_type: learn`
- `gt finalize` when the `.impl/plan.md` has `plan_type: learn`
```

**Update to:**
```markdown
- Identified by the `erk-learn` label on the GitHub issue
...
- `erk plan submit` when the source issue has the `erk-learn` label
- `gt finalize` when `.impl/issue.json` labels include `erk-learn`
```

### 2. `docs/learned/architecture/extraction-origin-tracking.md` - Lines 52-53

**Current (outdated):**
```markdown
- `erk plan submit` - Checks issue's `plan_type` field in plan-header metadata
- `gt finalize` - Checks `.impl/plan.md` for `plan_type: learn`
```

**Update to:**
```markdown
- `erk plan submit` - Checks if source issue has `erk-learn` label
- `gt finalize` - Checks if `.impl/issue.json` labels include `erk-learn`
```

### 3. Add Autolearn Documentation

No docs currently mention the `autolearn` feature. Add:

**`docs/learned/glossary.md`** - New entry after "Learn Plan":
```markdown
### Autolearn

An optional feature that automatically creates learn plans when landing PRs from plan branches. When enabled, `erk pr land` triggers insight extraction from the implementation session.

**Configuration**:
- Enable: `erk config set autolearn true`
- Disable: `erk config set autolearn false`
- Skip once: `erk pr land --no-autolearn`

**Behavior**: After successfully landing a PR, if autolearn is enabled and the branch is a plan branch (P{number}-...), erk creates a learn plan from the implementation session.

**Related**: [Learn Plan](#learn-plan)
```

**`docs/learned/planning/workflow.md`** - Add section on autolearn workflow.

## Files That Do NOT Need Updates

### `.claude/commands/erk/learn.md` - Line 209

Uses `--plan-type learn` which is **correct**. The CLI option still exists and works - it internally converts to the `erk-learn` label:

```python
if plan_type == "learn":
    extra_labels = ["erk-learn"]
```

This is a convenience abstraction. Keep it.

### `src/erk/cli/commands/exec/scripts/plan_save_to_issue.py`

The `--plan-type` option works correctly as a convenience wrapper. No deprecation needed - it's cleaner for agents to use `--plan-type learn` than `--extra-labels erk-learn`.

### Deprecated Files (Intentional)

- `src/erk/cli/commands/plan/learn/complete_cmd.py` - Correctly marked deprecated
- `tests/commands/plan/learn/test_complete.py` - Documents deprecation

## Implementation Steps

1. Edit `docs/learned/glossary.md`:
   - Line 854: Change metadata reference to label reference
   - Lines 869-870: Update detection methods to label-based
   - Add new "Autolearn" glossary entry after "Learn Plan"

2. Edit `docs/learned/architecture/extraction-origin-tracking.md`:
   - Lines 52-53: Update detection method descriptions

3. Add autolearn section to `docs/learned/planning/workflow.md`

## Verification

```bash
# Should return 0 matches in docs
grep -r "plan_type" docs/

# Should only match deprecated code files
grep -r "plan_type: learn" .
```