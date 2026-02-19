# Plan: Skill-side branching for plan-save backend messaging

## Context

PR #7499 makes plan-save messaging backend-aware by pushing display fields (`saved_as_label`, `view_command`, `next_steps`) into the Python JSON output, eliminating branching in the skill markdown. The user prefers the alternative: keep Python output minimal/factual and do the display branching in `plan-save.md` instead.

The rationale is separation of concerns — Python produces data, the skill handles presentation.

## Approach

### 1. Add a single `plan_backend` field to JSON output

Instead of 3 display fields, add one factual field to both backends' JSON output:

**`src/erk/cli/commands/exec/scripts/plan_save.py`** (`_save_as_draft_pr` output_data dict, ~line 217):
- Add `"plan_backend": "draft_pr"` to the output dict

**`src/erk/cli/commands/exec/scripts/plan_save_to_issue.py`** (output_data dict, ~line 308):
- Add `"plan_backend": "github"` to the output dict

No other Python changes. No `format_next_steps_draft_pr` function, no `view_pr` property, no display strings in Python.

### 2. Update JSON contract documentation in skill

**`.claude/commands/erk/plan-save.md`** line 27:
```
The JSON output contract is the same for both backends (`issue_number`, `issue_url`, `title`, `branch_name`, `plan_backend`).
```

### 3. Add backend branching to Step 4: Display Results

**`.claude/commands/erk/plan-save.md`** — Replace the current Step 4 display block (~lines 126-146) with branching instructions:

```markdown
### Step 4: Display Results

On success, display based on `plan_backend` from JSON output:

**Header (both backends):**
```
Plan "<title>" saved as <"draft PR" if plan_backend=="draft_pr", else "issue"> #<issue_number>
URL: <issue_url>
```

**If `plan_backend` is `"draft_pr"`:**
```
Next steps:

View PR: gh pr view <issue_number> --web

In Claude Code:
  Submit to queue: /erk:plan-submit — Submit plan for remote agent implementation

OR exit Claude Code first, then run one of:
  Local: erk prepare <issue_number>
  Prepare+Implement: source "$(erk prepare <issue_number> --script)" && erk implement --dangerous
  Submit to Queue: erk plan submit <issue_number>
```

**If `plan_backend` is `"github"` (or absent):**
```
Next steps:

View Issue: gh issue view <issue_number> --web

In Claude Code:
  Submit to queue: /erk:plan-submit — Submit plan for remote agent implementation
  Plan review: /erk:plan-review — Submit plan as PR for human review before implementation

OR exit Claude Code first, then run one of:
  Local: erk prepare <issue_number>
  Prepare+Implement: source "$(erk prepare <issue_number> --script)" && erk implement --dangerous
  Submit to Queue: erk plan submit <issue_number>
```

### 4. Fix verification failure message (Step 3)

**`.claude/commands/erk/plan-save.md`** line 92 — Add backend-aware label:
```
Fix: Close <"draft PR" if plan_backend=="draft_pr", else "issue"> #<issue_number> and re-run:
```

### 5. Update tests

**`tests/unit/cli/commands/exec/scripts/test_plan_save.py`**:
- Assert `output["plan_backend"] == "draft_pr"` (instead of the 3 display field assertions from #7499)

**`tests/unit/cli/commands/exec/scripts/test_plan_save_to_issue.py`**:
- Assert `output["plan_backend"] == "github"` (instead of the 3 display field assertions)

**No `tests/unit/test_next_steps.py`** — the `format_next_steps_draft_pr` function doesn't get created, so no tests needed for it. The existing `format_next_steps_plain` tests remain untouched.

### 6. No changes to `next_steps.py`

The `format_next_steps_draft_pr` function and `view_pr` property from PR #7499 are not needed. The existing `format_next_steps_plain` and `format_next_steps_markdown` remain unchanged.

## Files Modified

| File | Change |
|------|--------|
| `src/erk/cli/commands/exec/scripts/plan_save.py` | Add `"plan_backend": "draft_pr"` to output dict |
| `src/erk/cli/commands/exec/scripts/plan_save_to_issue.py` | Add `"plan_backend": "github"` to output dict |
| `.claude/commands/erk/plan-save.md` | Backend branching in Step 4 display, Step 3 failure msg, JSON contract doc |
| `tests/unit/cli/commands/exec/scripts/test_plan_save.py` | Assert `plan_backend` field |
| `tests/unit/cli/commands/exec/scripts/test_plan_save_to_issue.py` | Assert `plan_backend` field |

## What does NOT change (vs PR #7499)

- No `format_next_steps_draft_pr()` function in `next_steps.py`
- No `view_pr` property on `IssueNextSteps`
- No `saved_as_label` / `view_command` / `next_steps` fields in JSON output
- No `tests/unit/test_next_steps.py` new file

## Verification

1. Run `make fast-ci` to confirm all tests pass
2. Manually verify the skill markdown reads clearly — the branching instructions should be unambiguous for the agent