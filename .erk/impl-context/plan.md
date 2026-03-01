# Add `--skip-learn` option to `erk land`

## Context

When `erk land` merges a PR that was implemented from a plan, it automatically creates a "learn plan" draft PR to capture implementation insights from the associated sessions. This is controlled by the `prompt_learn_on_land` config setting (default: `True`).

Currently, the only ways to skip learn plan creation are:
1. Set `prompt_learn_on_land = false` in config (affects all future lands)
2. Land a PR that has the `erk-learn` label (cycle prevention)
3. Land a non-plan branch (no plan_id)

There is no way to skip the learn step for a single invocation without changing persistent config. This plan adds a `--skip-learn` CLI flag to `erk land` that suppresses learn plan creation for that specific invocation.

## Changes

### 1. Add `skip_learn` field to `LandState` (land_pipeline.py)

**File:** `src/erk/cli/commands/land_pipeline.py`

Add a `skip_learn: bool` field to the `LandState` frozen dataclass in the "CLI inputs" section (after `dry_run`):

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
    skip_learn: bool  # <-- NEW
    target_arg: str | None
    ...
```

Update `make_initial_state()` to accept and pass through `skip_learn`:
- Add `skip_learn: bool` parameter
- Pass it to `LandState(skip_learn=skip_learn, ...)`

Update `make_execution_state()` to accept and pass through `skip_learn`:
- Add `skip_learn: bool` parameter
- Pass it to `LandState(skip_learn=skip_learn, ...)`

### 2. Check `skip_learn` in the `create_learn_pr` pipeline step (land_pipeline.py)

**File:** `src/erk/cli/commands/land_pipeline.py`

In the `create_learn_pr()` function, add a check for `state.skip_learn` before calling `_create_learn_pr_with_sessions`:

```python
def create_learn_pr(ctx: ErkContext, state: LandState) -> LandState | LandError:
    """Create a learn plan as a draft PR with preprocessed sessions for the landed plan."""
    if state.plan_id is None or state.merged_pr_number is None:
        return state
    if state.skip_learn:
        return state

    _create_learn_pr_with_sessions(ctx, state=state)
    return state
```

### 3. Add `--skip-learn` CLI option to `erk land` (land_cmd.py)

**File:** `src/erk/cli/commands/land_cmd.py`

Add a new Click option to the `land` command. Place it after the `--no-delete` option:

```python
@click.option(
    "--skip-learn",
    "skip_learn",
    is_flag=True,
    help="Skip creating a learn plan after landing.",
)
```

Update the `land()` function signature to accept `skip_learn: bool`.

Pass `skip_learn` through to `make_initial_state()`:
```python
initial_state = make_initial_state(
    ...
    skip_learn=skip_learn,
)
```

Pass `skip_learn` through to both execution paths:

In `_land_target()` — add `skip_learn: bool` parameter and pass it to `render_land_execution_script()`.

In `_execute_land_directly()` — add `skip_learn: bool` parameter and pass it to `make_execution_state()`.

Update the call sites in `land()` that call `_land_target()` and `_execute_land_directly()` to pass `skip_learn`.

### 4. Thread `skip_learn` through the deferred execution script (land_cmd.py)

**File:** `src/erk/cli/commands/land_cmd.py`

In `render_land_execution_script()`:
- Add `skip_learn: bool` parameter
- Bake the flag into the generated shell script (similar to `--no-cleanup`):
  ```python
  if skip_learn:
      cmd_parts.append("--skip-learn")
  ```

### 5. Add `--skip-learn` to the exec script (land_execute.py)

**File:** `src/erk/cli/commands/exec/scripts/land_execute.py`

Add a Click option to `land_execute`:
```python
@click.option(
    "--skip-learn",
    "skip_learn",
    is_flag=True,
    help="Skip creating a learn plan",
)
```

Update the function signature and pass `skip_learn` to `_execute_land`:
```python
_execute_land(
    erk_ctx,
    ...
    skip_learn=skip_learn,
)
```

### 6. Thread `skip_learn` through `_execute_land` (land_cmd.py)

**File:** `src/erk/cli/commands/land_cmd.py`

In `_execute_land()`:
- Add `skip_learn: bool` parameter
- Pass it to `make_execution_state()`:
  ```python
  state = make_execution_state(
      ...
      skip_learn=skip_learn,
  )
  ```

### 7. Update the `/erk:land` slash command (land.md)

**File:** `.claude/commands/erk/land.md`

Update the slash command to:
1. Add `--skip-learn` to the argument-hint in the frontmatter:
   ```yaml
   argument-hint: "[branch|PR#|URL] [--skip-objective] [--skip-learn]"
   ```
2. In the "Parse Arguments" step, also check for `--skip-learn` flag
3. In the "Execute erk land" step, pass `--skip-learn` when the flag is present:
   ```bash
   erk land <PR_NUMBER> --force --skip-learn
   ```
4. Add `--skip-learn` to the fail-open behavior table:
   | `--skip-learn` flag passed | Land normally, skip learn |

### 8. Update tests

**File:** `tests/unit/cli/commands/land/test_land_learn.py`

Add a test for the new `skip_learn` behavior in `create_learn_pr`:

```python
def test_create_learn_pr_skips_when_skip_learn_is_set(tmp_path: Path) -> None:
    """Skips learn plan creation when skip_learn=True."""
    fake_issues = FakeGitHubIssues(username="testuser")
    fake_github = FakeGitHub(issues_gateway=fake_issues)
    ctx = context_for_test(github=fake_github, issues=fake_issues, cwd=tmp_path)
    state = _land_state(tmp_path, plan_id="100", merged_pr_number=99)
    state = replace(state, skip_learn=True)

    result = create_learn_pr(ctx, state)
    assert not isinstance(result, LandError)
    assert len(fake_github.created_prs) == 0
```

Update the `_land_state` helper to include `skip_learn=False` as the default.

## Files NOT Changing

- `src/erk/cli/commands/land_learn.py` — No changes needed. The `_should_create_learn_pr()` config check and `_create_learn_pr_with_sessions()` remain unchanged. The skip is handled at the pipeline step level in `land_pipeline.py`.
- `packages/erk-shared/src/erk_shared/context/types.py` — No new config fields. This is a per-invocation CLI flag, not a persistent config change.
- `src/erk/cli/config.py` — No config changes.
- `CHANGELOG.md` — Never modified directly per project rules.

## Implementation Details

### Design Decision: Pipeline step vs. config check

The `skip_learn` flag short-circuits at the `create_learn_pr()` pipeline step rather than modifying `_should_create_learn_pr()`. This keeps the config-based check separate from the CLI-based override. The config check answers "is learn enabled for this repo?" while the CLI flag answers "skip it this time."

### Pattern Followed

This follows the exact same pattern as `no_delete`:
1. CLI flag → LandState field → threaded through make_initial_state/make_execution_state
2. For deferred execution (--up/--down), baked into the shell script as a static flag
3. Checked in the execution pipeline before the operation

### Edge Cases

- `--skip-learn` + `--dry-run`: No interaction — dry-run exits before the execution pipeline runs.
- `--skip-learn` on a non-plan branch: No-op — learn step already skips when `plan_id is None`.
- `--skip-learn` with `prompt_learn_on_land=false`: Both suppress learn; no conflict.

## Verification

1. Run unit tests: `pytest tests/unit/cli/commands/land/test_land_learn.py -v`
2. Run type checker: `ty check src/erk/cli/commands/land_cmd.py src/erk/cli/commands/land_pipeline.py src/erk/cli/commands/exec/scripts/land_execute.py`
3. Run linter: `ruff check src/erk/cli/commands/land_cmd.py src/erk/cli/commands/land_pipeline.py src/erk/cli/commands/exec/scripts/land_execute.py`
4. Verify `erk land --help` shows the new `--skip-learn` flag
5. Integration test: Land a plan PR with `--skip-learn` and verify no learn plan draft PR is created