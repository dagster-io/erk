# Plan: Add `--ref` CLI Option to All Workflow Dispatch Commands

## Context

Today, the branch used for GitHub `workflow_dispatch` calls (the "ref") can only be configured globally via `.erk/config.toml` (`dispatch_ref` field) or per-user via `.erk/config.local.toml`. This means testing workflow changes on a feature branch requires modifying config — which either affects all users (repo config) or all of a developer's work streams (local config).

Adding a `--ref` CLI option to each dispatch command enables per-run override without touching config. Priority chain: `--ref` flag > config `dispatch_ref` > repository default branch.

## Commands to Update

| Command | File | How ref reaches gateway |
|---------|------|------------------------|
| `erk one-shot` | `src/erk/cli/commands/one_shot.py` → `one_shot_dispatch.py` | Via `dispatch_one_shot(ref=...)` |
| `erk launch` | `src/erk/cli/commands/launch_cmd.py` | Via `_dispatch_workflow(ref=...)` and `_dispatch_learn(ref=...)` |
| `erk pr dispatch` | `src/erk/cli/commands/pr/dispatch_cmd.py` | Via `_dispatch_planned_pr_plan(ref=...)` |

**Not touched:** `erk admin test-dispatch` (intentionally hardcodes `ref=current_branch`).

## Implementation Steps

### Step 1: Update FakeGitHub to capture ref

**File:** `packages/erk-shared/src/erk_shared/gateway/github/fake.py`

Currently `triggered_workflows` stores `tuple[str, dict[str, str]]` — only `(workflow, inputs)`. The `ref` parameter is silently dropped. Change to include ref as the third element:

- `_triggered_workflows` type: `list[tuple[str, dict[str, str], str | None]]`
- Append: `self._triggered_workflows.append((workflow, inputs, ref))`
- Property return type: `list[tuple[str, dict[str, str], str | None]]`

### Step 2: Fix all test destructuring sites

Every `workflow, inputs = github.triggered_workflows[0]` becomes `workflow, inputs, _ref = ...`. This is mechanical — ~34 sites across ~9 test files:

- `tests/unit/cli/commands/test_admin_test_workflow.py`
- `tests/unit/core/github/test_trigger_workflow.py`
- `tests/unit/core/test_workflow_smoke_test.py`
- `tests/commands/admin/test_plan_implement_workflow.py`
- `tests/commands/one_shot/test_one_shot.py`
- `tests/commands/one_shot/test_one_shot_dispatch.py`
- `tests/commands/launch/test_launch_cmd.py`
- `tests/commands/objective/test_plan_one_shot.py`
- `tests/commands/pr/test_dispatch.py`

Use `rename-swarm` or `libcst-refactor` agent to handle bulk changes.

### Step 3: Add `--ref` to `erk one-shot` and thread through `dispatch_one_shot`

**`src/erk/cli/commands/one_shot.py`:**
- Add `@click.option("--ref", "dispatch_ref", type=str, default=None, help="Branch to dispatch workflow from (overrides config dispatch_ref)")`
- Add `dispatch_ref: str | None` to function signature
- Resolve: `ref = dispatch_ref if dispatch_ref is not None else ctx.local_config.dispatch_ref`
- Pass: `dispatch_one_shot(ctx, params=params, dry_run=dry_run, ref=ref)`

**`src/erk/cli/commands/one_shot_dispatch.py`:**
- Add `ref: str | None` keyword parameter to `dispatch_one_shot()`
- Change line 338 from `ref=ctx.local_config.dispatch_ref` to `ref=ref`
- Show ref in dry-run output when explicitly set

**Update other callers of `dispatch_one_shot` to pass `ref=ctx.local_config.dispatch_ref`:**
- `src/erk/cli/commands/objective/plan_cmd.py` (lines 261, 719)
- `src/erk/core/workflow_smoke_test.py` (line 78)

### Step 4: Add `--ref` to `erk launch` and thread through helpers

**`src/erk/cli/commands/launch_cmd.py`:**
- Add same `--ref` option to `launch()` Click command
- Add `dispatch_ref: str | None` to `launch()` signature
- Resolve ref once in `launch()`: `ref = dispatch_ref if dispatch_ref is not None else ctx.local_config.dispatch_ref`
- Add `ref: str | None` param to `_dispatch_workflow()` — change its `trigger_workflow` call from `ref=ctx.local_config.dispatch_ref` to `ref=ref`
- Add `ref: str | None` param to `_dispatch_learn()` — same change
- Thread `ref=ref` from `launch()` into all dispatch helpers and `_dispatch_workflow`/`_dispatch_learn` calls

### Step 5: Add `--ref` to `erk pr dispatch` and thread through

**`src/erk/cli/commands/pr/dispatch_cmd.py`:**
- Add same `--ref` option to `pr_dispatch()` Click command
- Add `dispatch_ref: str | None` to `pr_dispatch()` signature
- Resolve ref: `ref = dispatch_ref if dispatch_ref is not None else ctx.local_config.dispatch_ref`
- Add `ref: str | None` param to `_dispatch_planned_pr_plan()` — change its `trigger_workflow` call from `ref=ctx.local_config.dispatch_ref` to `ref=ref`
- Thread `ref=ref` through the dispatch loop

### Step 6: Add tests for `--ref` threading

Add one test per command verifying the ref reaches `FakeGitHub.triggered_workflows[n][2]`:

- `tests/commands/one_shot/test_one_shot_dispatch.py` — test `dispatch_one_shot` with explicit `ref="custom-ref"`, assert `triggered_workflows[0][2] == "custom-ref"`
- `tests/commands/launch/test_launch_cmd.py` — test `erk launch pr-address --pr 123 --ref custom-branch`, assert ref captured
- `tests/commands/pr/test_dispatch.py` — test `erk pr dispatch 42 --ref custom-branch`, assert ref captured

### Step 7: Update docs

**`docs/learned/erk/dispatch-ref-config.md`:** Add section on CLI `--ref` override with priority chain and examples.

## Verification

1. Run affected unit tests: `uv run pytest tests/commands/one_shot/ tests/commands/launch/ tests/commands/pr/test_dispatch.py tests/unit/cli/commands/test_admin_test_workflow.py tests/unit/core/`
2. Run full fast-ci to catch any missed destructuring sites
3. Verify `erk one-shot --help`, `erk launch --help`, `erk pr dispatch --help` all show `--ref` option
