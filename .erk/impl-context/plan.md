# Plan: Migrate `erk exec pr-check-complete` to `erk pr check --stage=impl`

## Context

`erk exec pr-check-complete` is a near-duplicate of `erk pr check` — it runs the same 4 checks plus one extra: verifying `.erk/impl-context/` was cleaned up before submission. The duplication is a maintenance hazard: adding a new check to `erk pr check` requires remembering to add it to `pr_check_complete.py` too. Consolidating into a `--stage=impl` flag on `erk pr check` eliminates the duplication and makes the impl-specific check discoverable at the right surface.

## Changes

### 1. `src/erk/cli/commands/pr/check_cmd.py`

**Add a `PrCheck` named tuple** at module level to replace the bare `tuple[bool, str]` pattern used throughout:

```python
from typing import NamedTuple

class PrCheck(NamedTuple):
    passed: bool
    description: str
```

Update the checks list type annotation and all construction sites to use kwargs:
```python
checks: list[PrCheck] = []
checks.append(PrCheck(passed=True, description="Branch name and plan reference agree (#456)"))
checks.append(PrCheck(passed=False, description="..."))
```

Also update the iteration that reads the results:
```python
for check in checks:
    status = click.style("[PASS]", fg="green") if check.passed else click.style("[FAIL]", fg="red")
    user_output(f"{status} {check.description}")
failed_count = sum(1 for check in checks if not check.passed)
```

**Add `--stage` option** using `click.Choice(["impl"])`. When `stage == "impl"`, prepend the impl-context check:

```python
@click.option(
    "--stage",
    type=click.Choice(["impl"]),
    default=None,
    help="Run stage-specific checks. Use 'impl' to also verify .erk/impl-context/ was cleaned up.",
)
@click.pass_obj
def pr_check(ctx: ErkContext, stage: str | None) -> None:
```

Impl-context check (inserted first when `stage == "impl"`):
```python
if stage == "impl":
    impl_context_dir = repo_root / ".erk" / "impl-context"
    if impl_context_dir.exists():
        checks.append(PrCheck(passed=False, description=".erk/impl-context/ still present (should be removed before submission)"))
    else:
        checks.append(PrCheck(passed=True, description=".erk/impl-context/ not present (cleaned up)"))
```

Note: `repo_root` is already computed before the checks list is built, so no reordering needed.

### 2. `src/erk/cli/commands/exec/group.py`

Remove the import and `add_command` registration for `pr_check_complete`.

Lines to remove:
- `from erk.cli.commands.exec.scripts.pr_check_complete import pr_check_complete` (line 123)
- `exec_group.add_command(pr_check_complete, name="pr-check-complete")` (line 251)

### 3. Delete `src/erk/cli/commands/exec/scripts/pr_check_complete.py`

### 4. Delete `tests/unit/cli/commands/exec/scripts/test_pr_check_complete.py`

### 5. `tests/commands/pr/test_check.py`

Add 3 new tests for `--stage=impl` behavior (pass `["check", "--stage=impl"]` to `runner.invoke`):

- `test_pr_check_stage_impl_fails_when_impl_context_present` — creates `.erk/impl-context/`, expects `[FAIL] .erk/impl-context/ still present`
- `test_pr_check_stage_impl_passes_when_impl_context_absent` — no impl-context dir, expects `[PASS] .erk/impl-context/ not present (cleaned up)`
- `test_pr_check_stage_impl_all_checks_pass` — full happy path with `--stage=impl`, impl-context absent and all PR invariants valid

### 6. `.claude/commands/erk/plan-implement.md`

Update line 343: `erk exec pr-check-complete` → `erk pr check --stage=impl`

Also update the surrounding description on line 346 accordingly.

## Verification

```bash
# Run existing pr check tests + new ones
uv run pytest tests/commands/pr/test_check.py -v

# Confirm deleted exec command is gone
erk exec --help  # should not list pr-check-complete

# Confirm new flag works
erk pr check --help  # should show --stage option
```
