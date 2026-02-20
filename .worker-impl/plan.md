# Change draft PR next steps to use branch name instead of PR number

## Context

When a plan is saved as a draft PR, the "Next steps" output shows:

```
Local: erk br co 7646 && erk implement --dangerous
```

Users naturally think about checking out branches by name, not by PR number. The `erk br co` command should use the branch name (e.g., `plan-my-feature-02-20-1121`), while other commands like `erk plan submit` should continue using the PR number.

The branch name is already available in all relevant contexts — the plan-save command generates it and includes it in JSON output. This change surfaces the branch name in the human-readable "display" format output and in the Claude command documentation.

## Changes

### 1. `packages/erk-shared/src/erk_shared/output/next_steps.py`

**Add `branch_name` field to `DraftPRNextSteps` and update `checkout_and_implement` property.**

The `DraftPRNextSteps` frozen dataclass (line 30) currently has only `pr_number: int`. Add a `branch_name: str` field:

```python
@dataclass(frozen=True)
class DraftPRNextSteps:
    """Canonical commands for draft PR operations."""

    pr_number: int
    branch_name: str
```

Update the `checkout_and_implement` property (line 44-45) to use `self.branch_name`:

```python
@property
def checkout_and_implement(self) -> str:
    return f"erk br co {self.branch_name} && erk implement --dangerous"
```

**Update `format_draft_pr_next_steps_plain` function signature (line 70).**

Add `branch_name: str` parameter and pass it through:

```python
def format_draft_pr_next_steps_plain(pr_number: int, *, branch_name: str) -> str:
    """Format for CLI output (plain text) for draft PR plans."""
    s = DraftPRNextSteps(pr_number, branch_name)
```

Note: Use keyword-only parameter (after `*`) per erk coding conventions — no default values.

### 2. `src/erk/cli/commands/exec/scripts/plan_save.py`

**Update the call to `format_draft_pr_next_steps_plain` (line 246).**

The `branch_name` variable is already available in scope (generated at line 140 via `generate_draft_pr_branch_name()`). Change the call from:

```python
click.echo(format_draft_pr_next_steps_plain(plan_number))
```

to:

```python
click.echo(format_draft_pr_next_steps_plain(plan_number, branch_name=branch_name))
```

### 3. `.claude/commands/erk/plan-save.md`

**Update the draft PR next steps template (line 148).**

In the "Step 4: Display Results" section, change:

```
  Local: erk br co <issue_number> && erk implement --dangerous
```

to:

```
  Local: erk br co <branch_name> && erk implement --dangerous
```

Where `<branch_name>` comes from the JSON output's `branch_name` field. The JSON output already includes `branch_name` (see the JSON contract at line 253 of plan_save.py).

### 4. Tests: `tests/unit/cli/commands/exec/scripts/test_plan_save.py`

**Update `test_draft_pr_success_display` (line 75) to verify branch name appears in output.**

The current test asserts `"Branch: plan-" in result.output` but does not verify the next steps use the branch name. Add an assertion:

```python
assert "erk br co plan-" in result.output
```

This validates that the display output uses the branch name in the checkout command rather than the PR number.

## Files NOT Changing

- **`src/erk/cli/commands/exec/scripts/plan_save_to_issue.py`** — Uses `format_next_steps_plain()` (issue-based), not the draft PR version. Out of scope.
- **`src/erk/cli/commands/exec/scripts/plan_update_issue.py`** — Does not display next steps output at all.
- **TUI files** (`src/erk/tui/app.py`, `src/erk/tui/screens/plan_detail_screen.py`, `src/erk/tui/commands/registry.py`) — These already use `row.worktree_branch` for `erk br co` commands. Not related to the draft PR next steps output.
- **`packages/erk-shared/src/erk_shared/impl_folder.py`** — Uses branch_name in a different context (impl folder comment body). Out of scope.
- **Other `.claude/commands/` or `.claude/skills/` files** — Searched for `erk br co <issue_number>` patterns in draft PR context; only `plan-save.md` has this pattern.
- **`erk plan submit` commands** — Continue using PR number as intended per task requirements.

## Verification

1. **Unit tests pass**: Run `pytest tests/unit/cli/commands/exec/scripts/test_plan_save.py` — all tests should pass, including the updated display format test.
2. **Type checking passes**: Run `ty check` on the changed files — the new `branch_name` parameter should be correctly typed.
3. **Linting passes**: Run `ruff check` on the changed files.
4. **Manual verification**: The `format_draft_pr_next_steps_plain` function has exactly one caller (`plan_save.py:246`), confirmed by grep. No other callers need updating.
5. **Behavioral check**: After changes, `erk exec plan-save --format display` should output `erk br co plan-<slug>` instead of `erk br co <number>` in the "Local:" line, while the "Submit to queue:" line still shows `erk plan submit <number>`.