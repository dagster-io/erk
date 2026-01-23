# Plan: Prevent Empty Plan Issues from Being Created

## Problem

The learn workflow creates empty plan issues when PlanSynthesizer determines no documentation is needed. This happens because:

1. `erk exec plan-save-to-issue` has **no content validation** - only checks if file exists
2. The learn command in `.claude/commands/erk/learn.md` unconditionally calls `plan-save-to-issue`
3. Validation code exists (`validate-plan-content`) but isn't integrated

## Solution

Add defense-in-depth validation:

1. **Primary defense**: Add validation to `plan-save-to-issue` so ALL callers are protected
2. **Secondary defense**: Update learn workflow to validate before saving and branch to `completed_no_plan`

## Implementation

### Phase 1: Add Validation to `plan-save-to-issue`

**File:** `src/erk/cli/commands/exec/scripts/plan_save_to_issue.py`

1. Import the existing validation function:
   ```python
   from erk.cli.commands.exec.scripts.validate_plan_content import _validate_plan_content
   ```

2. After reading plan content (line ~213), before creating issue, add validation:
   ```python
   # Validate plan content before creating issue
   valid, error, details = _validate_plan_content(plan)
   if not valid:
       if output_format == "display":
           click.echo(f"Error: Plan validation failed: {error}", err=True)
       else:
           click.echo(json.dumps({
               "success": False,
               "error": f"Plan validation failed: {error}",
               "error_type": "validation_failed",
               "details": details,
           }))
       raise SystemExit(2)  # Distinct exit code for validation failures
   ```

3. Update docstring exit codes:
   ```
   Exit Codes:
       0: Success - plan extracted and issue created
       1: Error - no plan found, gh failure, etc.
       2: Validation failed - plan empty, too short, or lacks structure
   ```

### Phase 2: Update Learn Workflow Command

**File:** `.claude/commands/erk/learn.md`

Update Step 6 "Save Learn Plan to GitHub Issue" section (~lines 628-650) to validate before saving:

```markdown
#### Validate and Save Learn Plan

First validate the synthesized plan has actionable content:

```bash
cat .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/learn-plan.md | erk exec validate-plan-content
```

Parse the JSON output:
- If `valid: false` → Skip saving, proceed to Step 6b with `completed_no_plan`
- If `valid: true` → Continue with save below

**If plan is valid**, save it as a GitHub issue:

```bash
erk exec plan-save-to-issue \
    --plan-type learn \
    --plan-file .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/learn-plan.md \
    --session-id="${CLAUDE_SESSION_ID}" \
    --learned-from-issue <parent-issue-number> \
    --format json
```
```

Also clarify Step 6b branching logic to make the two paths explicit.

### Phase 3: Add Tests

**File:** `tests/unit/cli/commands/exec/scripts/test_plan_save_to_issue.py`

Add tests for validation rejection:

1. `test_plan_save_to_issue_rejects_empty_plan` - empty content returns exit code 2
2. `test_plan_save_to_issue_rejects_too_short_plan` - under 100 chars returns exit code 2
3. `test_plan_save_to_issue_rejects_unstructured_plan` - no headers/lists returns exit code 2
4. Verify no GitHub issue is created in any rejection case

## Files to Modify

| File | Change |
|------|--------|
| `src/erk/cli/commands/exec/scripts/plan_save_to_issue.py` | Add validation, exit code 2 |
| `.claude/commands/erk/learn.md` | Validate before save, branch logic |
| `tests/unit/cli/commands/exec/scripts/test_plan_save_to_issue.py` | Add rejection tests |

## Verification

1. Run existing tests to ensure no regressions:
   ```bash
   make fast-ci
   ```

2. Manual test: Create an empty plan file and verify `plan-save-to-issue` rejects it with exit code 2:
   ```bash
   echo "" > /tmp/empty-plan.md
   erk exec plan-save-to-issue --plan-file /tmp/empty-plan.md --format json
   echo $?  # Should be 2
   ```

3. Manual test: Create a valid plan file and verify it's accepted:
   ```bash
   echo "# Valid Plan\n\n- Step 1: Do thing\n- Step 2: Do other thing\n\nThis is a valid plan with enough content to pass validation." > /tmp/valid-plan.md
   erk exec plan-save-to-issue --plan-file /tmp/valid-plan.md --format json
   ```