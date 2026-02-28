# Fix: Embed session XML files in learn plans created by `erk land`

## Context

PR #8488 added `--session-xml-dir` to the `plan-save` CLI command so learn plans created via the `/erk:learn` skill embed preprocessed session XML files in the PR diff. However, `erk land` creates learn plans through a completely different code path (`land_learn.py` → `create_plan_draft_pr()`) that has no XML embedding support. PR #8493 — the learn plan auto-created when #8488 was landed — only contains `plan.md` and `ref.json`, with no session XML files.

The irony: the feature that was supposed to enable XML embedding didn't work for its own learn plan because it only covered one of two code paths.

## Approach

The preprocessing pipeline already runs during `erk land` (inside `_compute_session_stats` for the log summary display), but the XML chunks are discarded after computing byte sizes. Capture those chunks and thread them through to `create_plan_draft_pr`.

## Changes

### 1. `src/erk/cli/commands/land_learn.py` — Capture XML chunks from preprocessing

**`SessionStats`** — Add `xml_chunks: tuple[str, ...]` field to hold the actual XML content that's already being generated.

**`_compute_session_stats`** — Instead of `xml_bytes += sum(len(...))`, collect chunks into a list and compute `xml_size_kb` from them. Return chunks in the `SessionStats`.

**`_log_session_discovery`** — Change return type from `None` to `dict[str, str]`. After logging, build a files dict from each session's XML chunks with paths like `{IMPL_CONTEXT_DIR}/sessions/{prefix}-{sid}.xml` (or `-part{N}.xml` for multi-chunk). Add a small helper `_session_type_prefix()` that maps session ID → `"planning"` / `"impl"` / `"learn"` / `"unknown"` based on set membership.

**`_create_learn_pr_impl`** — Capture the return value from `_log_session_discovery` and pass it as `extra_files` to `create_plan_draft_pr`.

New import: `IMPL_CONTEXT_DIR` from `erk_shared.plan_store.planned_pr_lifecycle`.

### 2. `packages/erk-shared/src/erk_shared/plan_store/create_plan_draft_pr.py` — Accept extra files

Add `extra_files: dict[str, str] | None` parameter to `create_plan_draft_pr()`. In step 5 (commit files), merge `extra_files` into the files dict before calling `commit_files_to_branch`.

### 3. Update all callers of `create_plan_draft_pr` to pass `extra_files=None`

- `src/erk/cli/commands/exec/scripts/create_pr_from_session.py` (line 67)
- `src/erk/cli/commands/pr/create_cmd.py` (line 89)
- `packages/erk-shared/tests/unit/github/test_plan_issues.py` — helper function (line 49) + 3 direct calls (lines 481, 584, 629)

### 4. Tests

**`packages/erk-shared/tests/unit/github/test_plan_issues.py`** — Add test that `extra_files` entries are merged into committed files (check `fake_git.branch_commits[0].files` contains the extra paths).

**`tests/unit/cli/commands/test_land_learn.py`** (or wherever land_learn tests live) — Add test that `_log_session_discovery` returns XML files dict when sessions have content. Verify file naming matches `{prefix}-{sid}.xml` convention.

## File naming convention

Consistent with `preprocess_session.py`:
- Single chunk: `{type}-{session_id}.xml`
- Multiple chunks: `{type}-{session_id}-part{N}.xml`
- Types: `planning`, `impl`, `learn`, `unknown`

## Verification

1. Run `pytest tests/unit/cli/commands/exec/scripts/test_plan_save.py` — existing tests still pass
2. Run `pytest packages/erk-shared/tests/unit/github/test_plan_issues.py` — new + existing tests pass
3. Run `ty` and `ruff` for type/lint checks
4. Manually test with `erk land` on a real plan to confirm XML files appear in the learn plan PR diff
