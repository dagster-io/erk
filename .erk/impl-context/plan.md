# Plan: Use branch name instead of PR number in `erk br co` next steps

## Context

After saving a plan as a draft PR, the "Next steps" output shows `erk br co <PR_NUMBER>`. The user wants this to use `erk br co <BRANCH_NAME>` instead, since branch name is a more natural identifier for checkout.

The `branch_name` is already computed and available at the call site — it just needs to be threaded through the formatting functions.

## Changes

### 1. `packages/erk-shared/src/erk_shared/output/next_steps.py`

**Add `branch_name` field to `DraftPRNextSteps`:**

```python
@dataclass(frozen=True)
class DraftPRNextSteps:
    pr_number: int
    branch_name: str

    # checkout_and_implement uses branch_name with --script flag (source for shell activation):
    @property
    def checkout_and_implement(self) -> str:
        return f'source "$(erk br co {self.branch_name} --script)" && erk implement --dangerous'
```

**Update `format_draft_pr_next_steps_plain` signature:**

```python
def format_draft_pr_next_steps_plain(pr_number: int, *, branch_name: str) -> str:
    s = DraftPRNextSteps(pr_number, branch_name)
    ...
```

### 2. `src/erk/cli/commands/exec/scripts/plan_save.py` (line 246)

Pass `branch_name` to the formatter:

```python
click.echo(format_draft_pr_next_steps_plain(plan_number, branch_name=branch_name))
```

### 3. `.claude/commands/erk/plan-save.md` (line 148)

Update the example output template:

```
  Local: source "$(erk br co <branch_name> --script)" && erk implement --dangerous
```

## Verification

- Run `erk exec plan-save --help` to confirm CLI still works
- Run any existing tests for plan_save: `pytest tests/unit/cli/commands/exec/scripts/ -k plan_save`
- Run ty/ruff on changed files
