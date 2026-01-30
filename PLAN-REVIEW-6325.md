# Refactor Land Command to Function Pipeline

Refactor `land_cmd.py` (1,865 lines) following the same pattern as the submit pipeline refactoring (PR #6300).

## Context

The submit refactoring replaced a dual-path branching orchestration with a linear pipeline of `(ErkContext, SubmitState) -> SubmitState | SubmitError` steps and a frozen `SubmitState` dataclass. Land has the same structural problems (parameter explosion, scattered logic, 30+ functions in one file) but adds a key difference: it has a **two-phase architecture** (validation + deferred script execution) that must be preserved.

## Approach: Two Pipelines

Create `land_pipeline.py` with **two separate pipelines** bridged by the existing shell script serialization boundary.

### Data Types

```python
@dataclass(frozen=True)
class LandState:
    # CLI inputs
    cwd: Path
    force: bool
    script: bool
    pull_flag: bool
    no_delete: bool
    up_flag: bool
    dry_run: bool
    target_arg: str | None

    # Resolved target (populated by resolve_target)
    repo_root: Path
    main_repo_root: Path
    branch: str
    pr_number: int
    pr_details: PRDetails | None
    worktree_path: Path | None
    is_current_branch: bool
    use_graphite: bool
    target_child_branch: str | None

    # Derived (populated by later steps)
    objective_number: int | None
    plan_issue_number: int | None
    cleanup_confirmed: bool
    merged_pr_number: int | None

@dataclass(frozen=True)
class LandError:
    phase: str
    error_type: str
    message: str
    details: dict[str, str]
```

### Validation Pipeline (runs in `erk land` CLI)

| Step | Function | What it does |
|------|----------|-------------|
| 1 | `resolve_target` | Consolidates the 3 resolver functions. Dispatches by `target_arg` (None=current branch, digit/URL=PR, else=branch). Populates branch, pr_number, pr_details, worktree_path, is_current_branch, use_graphite, target_child_branch |
| 2 | `validate_pr` | Clean working tree check, PR state=OPEN, PR base=trunk (non-Graphite), unresolved comments |
| 3 | `check_learn_status` | Extract plan_issue_number from branch, check learn status, prompt if needed |
| 4 | `gather_confirmations` | Classify cleanup type, prompt for cleanup confirmation |
| 5 | `resolve_objective` | Look up objective for branch |

After the pipeline, the CLI handler (not a pipeline step) does: dry-run output, script generation, script writing. These stay in `land_cmd.py` because they have side effects (file I/O, SystemExit).

### Execution Pipeline (runs in `erk exec land-execute`)

| Step | Function | What it does |
|------|----------|-------------|
| 1 | `merge_pr` | Dispatch between Graphite (`execute_land_pr`) and simple GitHub merge. Sets merged_pr_number |
| 2 | `update_objective` | Call `prompt_objective_update` if objective_number is set |
| 3 | `update_learn_plan` | Update parent plan learn_status if this is a learn plan |
| 4 | `promote_tripwires` | Extract and promote tripwire candidates |
| 5 | `close_review_pr` | Close review PR if plan has one |
| 6 | `cleanup_and_navigate` | Dispatch cleanup by type, navigate. Terminal step (may SystemExit) |

Step signature: `(ErkContext, LandState) -> LandState | LandError`

Exception: Step 6 (`cleanup_and_navigate`) is the terminal step that handles navigation side effects. It may raise `SystemExit` like the current code. The pipeline runner handles this.

### Serialization Boundary (unchanged)

The shell script bridges the two pipelines. Baked-in flags: `--pr-number`, `--branch`, `--worktree-path`, `--is-current-branch`, `--objective-number`, `--use-graphite`. User flags via `"$@"`: `--up`, `--no-pull`, `--no-delete`, `-f`.

`make_execution_state()` factory re-derives `repo_root`, `main_repo_root`, `pr_details`, `plan_issue_number`, `target_child_branch` from exec script args.

## Files

### New
- **`src/erk/cli/commands/land_pipeline.py`** (~600 lines) - LandState, LandError, all pipeline step functions, `run_validation_pipeline()`, `run_execution_pipeline()`, `make_initial_state()`, `make_execution_state()`

### Modified
- **`src/erk/cli/commands/land_cmd.py`** - Shrink to ~300-400 lines: Click command, `render_land_execution_script()`, `parse_argument()`, `resolve_branch_for_pr()`, wiring code that calls pipelines
- **`src/erk/cli/commands/exec/scripts/land_execute.py`** - Update imports

### Dead Code Removal
- **`_execute_simple_land`** - Defined at line 1252 but never called from production code (duplicated in `_execute_land`)
- **`CleanupContext`** - Replaced by `LandState` threading through all cleanup functions

### Gateway
- **`land_pr.py`** - Keep initially. The `execute_land_pr()` gateway does real work (child re-parenting, remote branch deletion). Redundant validation removal can be a follow-up.

## Pure Functions That Stay As-Is

These pure functions move to `land_pipeline.py` but keep their signatures:
- `determine_cleanup_type()` - pure classification, well-tested
- `parse_argument()` - stays in `land_cmd.py` (CLI layer)
- `resolve_branch_for_pr()` - stays in `land_cmd.py` (CLI layer)
- `check_unresolved_comments()` - moves to pipeline module
- `render_land_execution_script()` - stays in `land_cmd.py`

## Test Migration

### Existing tests (13 files, ~3,700 lines)

| Test File | Impact |
|-----------|--------|
| `test_parse_argument.py` | None - pure function stays in land_cmd |
| `test_determine_cleanup_type.py` | Low - import path changes |
| `test_find_assignment.py` | None |
| `test_render_land_script.py` | None |
| `test_resolvers.py` | Moderate - tests redirect to `resolve_target` step |
| `test_validate_pr_for_landing.py` | Moderate - tests redirect to `validate_pr` step |
| `test_cleanup_and_navigate.py` | Moderate - `LandState` replaces `CleanupContext` |
| `test_learn_status.py` | Low - function moves to pipeline |
| `test_update_parent_learn_status.py` | Low |
| `test_simple_land.py` | Remove - tests dead code `_execute_simple_land` |
| `test_dry_run.py` | Low |
| `test_no_delete_flag.py` | Low |

### New tests

```
tests/unit/cli/commands/land/pipeline/
    test_resolve_target.py
    test_validate_pr.py
    test_check_learn_status.py
    test_gather_confirmations.py
    test_merge_pr.py
    test_update_objective.py
    test_execute_cleanup.py
    test_run_validation_pipeline.py
    test_run_execution_pipeline.py
```

## Implementation Sequence

1. Create `land_pipeline.py` with data types and empty pipeline runners
2. Implement `resolve_target` step (consolidating 3 resolvers)
3. Implement `validate_pr` step
4. Implement `check_learn_status` and `gather_confirmations` steps
5. Implement `resolve_objective` step
6. Wire validation pipeline into `land()` CLI command
7. Implement execution pipeline steps (merge, objective, learn, tripwires, review PR, cleanup)
8. Wire execution pipeline into `_execute_land`
9. Remove dead code (`_execute_simple_land`, `CleanupContext`)
10. Update existing test imports, add new pipeline tests

## Verification

1. Run `make fast-ci` after each step to catch regressions
2. Run existing land tests: `pytest tests/unit/cli/commands/land/ -x`
3. Run exec script tests: `pytest tests/unit/cli/commands/exec/scripts/ -k land -x`
4. Full CI: `make all-ci`