# Plan: Refactor PR Submit to Function Pipeline

Replace the dual-path branching orchestration in `erk pr submit` with a linear pipeline of plain functions transforming a frozen `SubmitState` dataclass. No ABCs, Protocols, or strategy objects.

## New File

**`src/erk/cli/commands/pr/submit_pipeline.py`** — all pipeline logic lives here.

### Data Types

```python
@dataclass(frozen=True)
class SubmitState:
    cwd: Path
    repo_root: str
    branch_name: str
    parent_branch: str
    trunk_branch: str
    use_graphite: bool
    force: bool
    debug: bool
    session_id: str
    issue_number: int | None = None
    pr_number: int | None = None
    pr_url: str | None = None
    was_created: bool = False
    base_branch: str | None = None
    graphite_url: str | None = None
    diff_file: Path | None = None
    plan_context: PlanContext | None = None
    title: str | None = None
    body: str | None = None

@dataclass(frozen=True)
class SubmitError:
    phase: str
    error_type: str
    message: str
    details: dict[str, str]
```

### Pipeline Steps

Each step: `(ErkContext, SubmitState) -> SubmitState | SubmitError`

1. **`prepare_state()`** — Resolve repo_root, branch_name, parent_branch, trunk_branch, issue_number. Single location for all discovery. Consolidates the 3 duplicate parent-branch and 3 duplicate issue-number discovery sites.

2. **`commit_wip()`** — Check `has_uncommitted_changes()`, if so `add_all` + `commit`. Replaces 2 duplicate WIP commit sites (`submit_cmd.py:317-320`, `submit.py:170-174`).

3. **`push_and_create_pr()`** — Internal `if state.use_graphite` dispatch:
   - **Graphite path**: `gt submit`, then query GitHub for PR info. Inlines `_run_graphite_first_flow`.
   - **Core path**: Auth check, divergence check, `git push`, `gh pr create` or detect existing. Inlines `execute_core_submit`.
   - Both paths populate `pr_number`, `base_branch`, `graphite_url`, `was_created`.

4. **`extract_diff()`** — Local `git diff` to base branch, filter lock files, truncate, write scratch file. Inlines `execute_diff_extraction`.

5. **`fetch_plan_context()`** — `PlanContextProvider.get_plan_context()`, populate `plan_context`.

6. **`generate_description()`** — `CommitMessageGenerator` + `run_commit_message_generation()`, populate `title`/`body`.

7. **`enhance_with_graphite()`** — No-op if `graphite_url` already set (graphite-first path). Otherwise check auth + tracking, run `gt submit` idempotently. Inlines `execute_graphite_enhance`.

8. **`finalize_pr()`** — Update PR title/body with footer, add labels, amend local commit, clean up diff file. Inlines `execute_finalize`. Populates `pr_url`.

### Pipeline Runner

```python
PIPELINE = [
    prepare_state,
    commit_wip,
    push_and_create_pr,
    extract_diff,
    fetch_plan_context,
    generate_description,
    enhance_with_graphite,
    finalize_pr,
]

def run_submit_pipeline(ctx: ErkContext, state: SubmitState) -> SubmitState | SubmitError:
    for step in PIPELINE:
        result = step(ctx, state)
        if isinstance(result, SubmitError):
            return result
        state = result
    return state
```

## Files to Modify

| File                                                                   | Change                                                                                                                                                                                           |
| ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **NEW** `src/erk/cli/commands/pr/submit_pipeline.py`                   | All pipeline steps, data types, runner                                                                                                                                                           |
| `src/erk/cli/commands/pr/submit_cmd.py`                                | Shrink to CLI entry + `render_success()`. Delete `_run_graphite_first_flow`, `_run_core_submit`, `_run_diff_extraction`, `_run_graphite_enhance`, `_run_finalize`. Call `run_submit_pipeline()`. |
| `packages/erk-shared/src/erk_shared/gateway/pr/submit.py`              | Delete `execute_core_submit`. Keep `has_body_footer`, `has_checkout_footer_for_pr`, `has_issue_closing_reference`, `_make_divergence_error` utilities.                                           |
| `packages/erk-shared/src/erk_shared/gateway/pr/graphite_enhance.py`    | Delete `execute_graphite_enhance`. Keep `should_enhance_with_graphite`, `GraphiteCheckResult`.                                                                                                   |
| `packages/erk-shared/src/erk_shared/gateway/pr/diff_extraction.py`     | Delete `execute_diff_extraction`. Keep `filter_diff_excluded_files`.                                                                                                                             |
| `packages/erk-shared/src/erk_shared/gateway/gt/operations/finalize.py` | Delete `execute_finalize`. Keep `is_learn_plan`, `_extract_closing_ref_from_pr`.                                                                                                                 |
| `packages/erk-shared/src/erk_shared/gateway/pr/types.py`               | Delete entirely (`CoreSubmitResult`, `CoreSubmitError`, `GraphiteEnhanceResult`, `GraphiteEnhanceError`, `GraphiteSkipped` all replaced).                                                        |
| `packages/erk-shared/src/erk_shared/gateway/gt/types.py`               | Remove `FinalizeResult`, `PostAnalysisError`, `PostAnalysisErrorType`. Keep non-submit types.                                                                                                    |

## Files to Check for Imports of Deleted Types

Need to grep for all consumers of deleted types/functions and update them:

- `CoreSubmitResult`, `CoreSubmitError` — `submit_cmd.py` (primary), possibly tests
- `GraphiteEnhanceResult`, `GraphiteEnhanceError`, `GraphiteSkipped` — `submit_cmd.py`, possibly tests
- `FinalizeResult`, `PostAnalysisError` — `submit_cmd.py`, possibly tests
- `execute_core_submit`, `execute_graphite_enhance`, `execute_diff_extraction`, `execute_finalize` — `submit_cmd.py` (primary)
- `ProgressEvent`, `CompletionEvent` — may become unused in some modules after deletion

## Implementation Order

1. Create `submit_pipeline.py` with `SubmitState`, `SubmitError`, all 8 step functions, and `run_submit_pipeline()`
2. Rewrite `submit_cmd.py` to call `run_submit_pipeline()` and render results
3. Delete dead gateway functions and types
4. Fix all broken imports across the codebase
5. Update tests

## Progress Output

Pipeline steps call `click.echo` directly for progress output (matching existing `_run_graphite_first_flow` pattern). The `debug` flag on `SubmitState` controls verbose output. This is simpler than the Generator/Event pattern and sufficient since submit is always CLI-driven.

## Verification

1. Run existing tests: `pytest tests/ -k submit` to find all submit-related tests
2. Run full test suite to catch import breakage
3. Manual test: `erk pr submit` on a Graphite-tracked branch (graphite-first path)
4. Manual test: `erk pr submit --no-graphite` (core-only path)
5. Manual test: `erk pr submit` on a non-tracked branch (core + graphite enhance path)
6. Run `ty` for type checking
7. Run `ruff` for lint
