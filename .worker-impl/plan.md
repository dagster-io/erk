# Documentation Plan: Learn Plan Identification

## Context

This plan updates the existing Learn Plan glossary entry to document the `erk-learn` issue label and related identification patterns.

### Key Files Discovered

- `src/erk/cli/constants.py:27` - Defines `ERK_LEARN_LABEL = "erk-learn"`
- `src/erk/cli/commands/submit.py:79-88` - `is_issue_learn_plan()` helper function
- `src/erk/cli/commands/land_cmd.py:72-91` - Uses label to skip learn status check
- `src/erk/cli/commands/plan/learn/complete_cmd.py:49-54` - Validates issue has label
- `src/erk/cli/commands/exec/scripts/plan_save_to_issue.py:160-163` - Adds label when creating learn plans

### Existing Documentation

- `docs/learned/glossary.md` - Has "Learn Plan" entry but missing `erk-learn` label details
- `docs/learned/architecture/learn-origin-tracking.md` - Covers PR extraction skip behavior

## Raw Materials

https://gist.github.com/schrockn/a0bbe7c619508f11ee3f2076e96a302e

## Documentation Items

### Item 1: Update Learn Plan Glossary Entry

**Location:** `docs/learned/glossary.md` - "Learn Plan" section
**Action:** Update existing entry

**Current content (partial):**
```markdown
**Characteristics**:
- Labeled with `erk-plan`
- Created from session analysis to capture valuable insights
- Contains documentation items rather than code changes
- Marked with `plan_type: learn` in the plan-header metadata
- PRs from learn plans receive the `erk-skip-extraction` label
```

**Add after "Labeled with `erk-plan`":**
```markdown
- **Issue identification**: Issues have the `erk-learn` label (in addition to `erk-plan`)
```

**Add new section before "Purpose":**
```markdown
**Identifying Learn Plans in Code**:
- Issue label: Check for `erk-learn` in `issue.labels`
- Helper function: `is_issue_learn_plan(labels)` in `src/erk/cli/commands/submit.py`
- Plan metadata: Check `plan_type: learn` in plan-header
- PR label: PRs from learn plans have `erk-skip-extraction`

**Special Behaviors**:
- `erk land` skips the "not learned from" warning for learn plans (they don't need learning)
- `erk plan learn complete` validates the issue has the `erk-learn` label
```

**Source:** [Impl] Implementation added `erk-learn` check to skip learn status warning