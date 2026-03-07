# Hide Stub Branches from `erk br list` by Default

## Context

When running `erk br list`, stub branches (e.g., `__erk-slot-09-br-stub__`) are shown alongside real development branches. These stub branches are placeholder branches for empty worktree pool slots and have no meaningful content. They clutter the output and make it harder to see actual work branches.

The `erk wt list` command already handles this correctly — it hides placeholder branches by default and offers `-a`/`--all` to show them. This plan brings the same behavior to `erk br list`.

## Changes

### 1. Modify `src/erk/cli/commands/branch/list_cmd.py`

**Add import for `is_placeholder_branch`:**

Add to the imports at the top of the file:

```python
from erk.cli.commands.slot.common import is_placeholder_branch
```

**Add `--all` / `-a` flag to the command:**

Add a Click option matching the pattern used in `erk wt list` (`src/erk/cli/commands/wt/list_cmd.py:319-325`):

```python
@click.option(
    "-a",
    "--all",
    "show_all",
    is_flag=True,
    help="Show all branches including empty slot stubs",
)
```

This goes between the `@click.command("list")` and `@click.pass_obj` decorators. The function signature changes from `branch_list(ctx: ErkContext)` to `branch_list(ctx: ErkContext, show_all: bool)`.

**Add filtering logic after building `active_branches`:**

After the two loops that populate `active_branches` (after line 49, before the "Display table" section), add:

```python
# Filter out placeholder branches (empty slot stubs) unless --all is specified
if not show_all:
    active_branches = {
        branch: info
        for branch, info in active_branches.items()
        if not is_placeholder_branch(branch)
    }
```

This mirrors the filtering approach used in `erk wt list` (lines 204-208), adapted for the dict-based data structure in `branch_list`.

### 2. Add tests in `tests/unit/cli/commands/branch/test_list_cmd.py`

Add three new test functions at the end of the existing test file, following the established test patterns (using `erk_inmem_env`, `FakeGit`, `CliRunner`, `strip_ansi`):

**Test 1: `test_branch_list_hides_stub_branches_by_default`**

- Set up worktrees that include both a real feature branch and a stub branch (`__erk-slot-02-br-stub__`)
- Invoke `["branch", "list"]` without flags
- Assert the feature branch appears in output
- Assert the stub branch name does NOT appear in output

**Test 2: `test_branch_list_all_flag_shows_stub_branches`**

- Same setup as Test 1
- Invoke `["branch", "list", "--all"]`
- Assert BOTH the feature branch and stub branch appear in output

**Test 3: `test_branch_list_short_all_flag`**

- Same setup as Test 1
- Invoke `["branch", "list", "-a"]`
- Assert stub branch appears in output (validates short flag alias)

Follow the exact test patterns from the existing file. Each test uses `CliRunner`, `erk_inmem_env`, `FakeGit` with `worktrees`, `current_branches`, and `git_common_dirs`. Use `strip_ansi` on output for string assertions.

## Files NOT Changing

- `src/erk/cli/commands/wt/list_cmd.py` — already has this behavior, no changes needed
- `src/erk/cli/commands/slot/common.py` — `is_placeholder_branch` already exists and is correct
- No changes to gateway ABCs, fakes, or shared types
- No changes to CHANGELOG.md

## Implementation Details

- The `is_placeholder_branch` function from `slot/common.py` uses regex `r"^__erk-slot-\d+-br-stub__$"` — this is the canonical detection function
- The flag uses `show_all` as the Python parameter name (matching `wt list`), with `"show_all"` as the Click argument name to avoid conflict with the Python builtin `all`
- Stub branches enter `active_branches` via the worktree loop (lines 40-44), since they have worktrees. They would not enter via the PR loop since they have no PRs. The filter after both loops handles both paths correctly
- The docstring should be updated to mention the `--all` flag behavior

## Verification

1. Run the new unit tests: `pytest tests/unit/cli/commands/branch/test_list_cmd.py -v`
2. Run existing tests to ensure no regressions: `pytest tests/unit/cli/commands/branch/ -v`
3. Run type checker: `ty check src/erk/cli/commands/branch/list_cmd.py`
4. Run linter: `ruff check src/erk/cli/commands/branch/list_cmd.py`