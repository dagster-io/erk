# Add `--ref` and `--ref-current` flags to dispatch commands

## Context

The `--ref` flag (for overriding `dispatch_ref` from config) exists on `erk launch`, `erk pr dispatch`, and `erk one-shot`, but is missing from two commands that also dispatch workflows:

- `erk workflow smoke-test` — hardcodes `ctx.local_config.dispatch_ref`
- `erk objective plan` — hardcodes `ctx.local_config.dispatch_ref`

Additionally, all dispatch commands should support `--ref-current` as a convenience flag to dispatch from the current branch without typing its name.

## Changes

### 1. Add `--ref` to `erk workflow smoke-test`

**`src/erk/cli/commands/doctor_workflow.py`** (~line 221):
- Add `@click.option("--ref", "dispatch_ref", ...)` and `@click.option("--ref-current", is_flag=True, ...)` to `workflow_smoke_test_cmd`
- Pass both to `_handle_smoke_test` → `run_smoke_test`

**`src/erk/core/workflow_smoke_test.py`** (`run_smoke_test`):
- Add `dispatch_ref: str | None` parameter
- Resolve ref with same pattern as other commands

### 2. Add `--ref` to `erk objective plan`

**`src/erk/cli/commands/objective/plan_cmd.py`** (~line 505):
- Add `@click.option("--ref", "dispatch_ref", ...)` and `@click.option("--ref-current", is_flag=True, ...)`
- Thread to both `dispatch_one_shot` call sites (lines 289, 751)

### 3. Add `--ref-current` flag to all 5 dispatch commands

Add to each command:
```python
@click.option("--ref-current", is_flag=True, default=False, help="Dispatch workflow from the current branch")
```

Resolution logic (at each command's ref resolution point):
```python
if ref_current:
    ref = ctx.git.branch.get_current_branch(repo.root)
else:
    ref = dispatch_ref if dispatch_ref is not None else ctx.local_config.dispatch_ref
```

`--ref` and `--ref-current` are mutually exclusive — if both provided, error.

Apply at:
- `src/erk/cli/commands/launch_cmd.py` (line 462)
- `src/erk/cli/commands/one_shot.py` (line 126)
- `src/erk/cli/commands/pr/dispatch_cmd.py` (line 420)
- `src/erk/cli/commands/doctor_workflow.py` (new)
- `src/erk/cli/commands/objective/plan_cmd.py` (new, two call sites)

### 4. Extract shared ref resolution helper

Since the same 4-line pattern repeats in 6 places, extract a helper:

**`src/erk/cli/commands/ref_resolution.py`** (new file):
```python
def resolve_dispatch_ref(
    ctx: ErkContext, *, dispatch_ref: str | None, ref_current: bool
) -> str | None:
    if ref_current and dispatch_ref is not None:
        raise click.UsageError("--ref and --ref-current are mutually exclusive")
    if ref_current:
        branch = ctx.git.branch.get_current_branch(ctx.repo.root)
        if branch is None:
            raise click.UsageError("--ref-current requires being on a branch (not detached HEAD)")
        return branch
    return dispatch_ref if dispatch_ref is not None else ctx.local_config.dispatch_ref
```

Then each command just calls `ref = resolve_dispatch_ref(ctx, dispatch_ref=dispatch_ref, ref_current=ref_current)`.

## Files to modify

1. `src/erk/cli/commands/ref_resolution.py` — **new** shared helper
2. `src/erk/cli/commands/doctor_workflow.py` — add `--ref` + `--ref-current`
3. `src/erk/core/workflow_smoke_test.py` — accept `dispatch_ref` parameter
4. `src/erk/cli/commands/objective/plan_cmd.py` — add `--ref` + `--ref-current`
5. `src/erk/cli/commands/launch_cmd.py` — add `--ref-current`, use shared resolver
6. `src/erk/cli/commands/one_shot.py` — add `--ref-current`, use shared resolver
7. `src/erk/cli/commands/pr/dispatch_cmd.py` — add `--ref-current`, use shared resolver

## Verification

- `erk workflow smoke-test --help` shows `--ref` and `--ref-current`
- `erk objective plan --help` shows `--ref` and `--ref-current`
- `erk launch --help` shows `--ref-current`
- Passing both `--ref` and `--ref-current` produces a usage error
- Run existing tests
