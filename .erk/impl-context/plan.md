# Objective: Eliminate `.impl/` Folder — Unify on `.erk/impl-context/<branch>/`

## Context

The codebase currently has two folders for plan context:
- `.erk/impl-context/<branch>/` — committed staging area (visible in PRs)
- `.impl/` — local-only copy (never committed), created by copying from impl-context

This dual-folder architecture adds complexity and confusion. The CI workflow copies `.erk/impl-context/` to `.impl/` before implementation, and all runtime code reads from `.impl/`. The goal is to eliminate `.impl/` entirely and make `.erk/impl-context/<branch>/` the sole location for all plan context.

## Scope

~100 source/test files with behavioral changes, plus ~80 doc/command/skill files with text updates.

This is an **objective** with 4 phases, each becoming a separate plan/PR.

## Phase 1: Core Behavioral Changes (~45 files)

### 1a. Core module: `packages/erk-shared/src/erk_shared/impl_folder.py`

- **`resolve_impl_dir()`**: Remove Step 2 (lines 77-80, legacy `.impl/` fallback). Resolution becomes: branch-scoped → discovery scan → None
- **`read_plan_ref()`**: Remove legacy `issue.json` fallback (lines 328-357). Keep `plan-ref.json` and `ref.json`
- **`has_plan_ref()`**: Remove `issue.json` check (line 372)
- Update all docstrings: `.impl/` → "impl directory" or ".erk/impl-context/"

### 1b. Replace all hardcoded `cwd / ".impl"` paths

Each of these must use `resolve_impl_dir()` or `get_impl_dir()`:

| File | Line | Change |
|------|------|--------|
| `src/erk/core/workflow_display.py` | 34 | `resolve_impl_dir(worktree_path, branch_name=None)` |
| `src/erk/cli/commands/exec/scripts/setup_impl_from_pr.py` | 130 | `resolve_impl_dir(cwd, branch_name=None)` |
| `src/erk/cli/commands/pr/submit_pipeline.py` | 801 | `resolve_impl_dir(state.cwd, branch_name=...)` |
| `src/erk/cli/commands/exec/scripts/objective_link_pr.py` | 39 | Replace `_find_impl_dir()` body with `resolve_impl_dir()` |
| `src/erk/cli/commands/slot/common.py` | 504 | Remove `.impl/` cleanup, keep `.erk/impl-context/` cleanup |
| `src/erk/cli/commands/exec/scripts/setup_impl.py` | 196 | `resolve_impl_dir(cwd, branch_name=...)` |
| `src/erk/cli/commands/wt/create_cmd.py` | 642,933-934 | Use `resolve_impl_dir()` for source, `get_impl_dir()` for dest |

### 1c. Health checks and init

- `src/erk/core/health_checks.py:674`: Remove `.impl/` from `required_entries`
- `src/erk/cli/commands/init/main.py:229-233`: Remove `.impl/` gitignore prompt

### 1d. Update tests for Phase 1

All tests creating `tmp_path / ".impl"` → `tmp_path / ".erk" / "impl-context" / "<branch>"`:

- `tests/core/test_impl_folder.py` — Remove legacy fallback tests
- `tests/core/test_health_checks.py` — Update required entries
- `tests/tui/data/test_provider.py` — 6 occurrences
- `tests/commands/test_dash_workflow_runs.py` — 10 occurrences
- `tests/commands/test_create_copy_impl.py` — 8 occurrences
- `tests/commands/pr/test_check.py` — 2 occurrences
- `tests/commands/pr/test_dispatch.py` — 2 occurrences
- `tests/commands/pr/test_list.py` — 4 occurrences
- `tests/commands/setup/init/test_gitignore.py` — Update assertions
- `tests/unit/cli/commands/exec/scripts/test_setup_impl.py`
- `tests/unit/cli/commands/exec/scripts/test_setup_impl_from_pr.py`
- `tests/unit/cli/commands/exec/scripts/test_impl_verify.py`
- `tests/unit/cli/commands/exec/scripts/test_objective_link_pr.py`
- `tests/unit/cli/commands/exec/scripts/test_mark_impl_started_ended.py`
- `tests/unit/cli/commands/pr/submit_pipeline/test_link_pr_to_objective_nodes.py`
- `tests/unit/cli/commands/slot/test_assign_cmd.py`
- `tests/unit/cli/commands/branch/test_create_cmd.py`
- `tests/commands/branch/test_checkout_cmd.py`
- `tests/commands/implement/test_file_mode.py`
- `tests/commands/implement/test_issue_mode.py`
- `tests/integration/cli/commands/exec/scripts/test_check_impl_integration.py`

## Phase 2: CI Workflows (~5 files)

### 2a. `.github/workflows/plan-implement.yml`

- **Remove copy step** (lines 195-205): Instead of `cp -r .erk/impl-context .impl`, write `run-info.json` directly into the impl-context subdir
- **Change cleanup** (lines 207-223): `git rm -rf .erk/impl-context/` → `git rm -r --cached .erk/impl-context/` (untrack from git but keep on disk; `.gitignore` already has `.erk/impl-context/`)
- **Update filters** (lines 310-311): Remove `.impl/` from uncommitted changes filter

### 2b. `.github/workflows/one-shot.yml`

- **Remove `.impl/` creation** (lines 107-118): Read prompt directly from `.erk/impl-context/`, or write workflow input to `.erk/impl-context/` dir
- **Update output checks** (lines 165-180): Check `.erk/impl-context/` instead of `.impl/`
- **Remove copy-to-impl-context step** (lines 231-233): Plan is already written to `.erk/impl-context/`

### 2c. `.github/workflows/ci.yml:259`

- `if [ -d ".impl" ]` → `if [ -d ".erk/impl-context" ]`

## Phase 3: Claude Commands and Skills (~13 files)

### Commands to update

| File | Occurrences | Key Changes |
|------|-------------|-------------|
| `.claude/commands/erk/plan-implement.md` | 15 | Entire workflow references |
| `.claude/commands/erk/one-shot-plan.md` | 8 | Read/write paths |
| `.claude/commands/erk/git-pr-push.md` | 3 | `.impl` dir check → impl-context check |
| `.claude/commands/erk/pr-submit.md` | 1 | ref.json path |
| `.claude/commands/erk/land.md` | 1 | plan-ref.json check |
| `.claude/commands/erk/objective-plan.md` | 1 | plan-ref.json path |
| `.claude/commands/local/plan-update.md` | 1 | issue.json reference |

### Skills to update

| File | Key Changes |
|------|-------------|
| `.claude/skills/erk-exec/reference.md` | Command descriptions |
| `.claude/skills/erk-exec/SKILL.md` | Command table |
| `.claude/skills/erk-planning/references/workflow.md` | Workflow integration |
| `.claude/skills/erk-planning/SKILL.md` | Plan reference paths |
| `.claude/skills/learned-docs/SKILL.md` | read_when example |
| `.claude/agents/changelog/commit-categorizer.md` | Exclusion path |

## Phase 4: Documentation and Comments (~90 files)

### Source code docstrings/comments (~15 files)

Update `.impl/` references in comments and user-facing strings:
- Exec scripts: `check_impl.py`, `impl_init.py`, `impl_verify.py`, `mark_impl_started.py`, `mark_impl_ended.py`, `upload_impl_session.py`, `exit_plan_mode_hook.py`, `detect_plan_from_branch.py`, `get_learn_sessions.py`, `track_learn_evaluation.py`
- CLI commands: `learn_cmd.py`, `branch/create_cmd.py`, `branch/checkout_cmd.py`, `wt/list_cmd.py`, `pr/dispatch_cmd.py`
- Status: `status/collectors/impl.py`, `status/models/status_data.py`
- Agent docs: `agent_docs/operations.py`
- Scripts: `exec/scripts/AGENTS.md`

### Learned docs (~70 files in `docs/learned/`)

Update all `.impl/` references. Highest-impact files:
- `docs/learned/architecture/impl-folder-lifecycle.md` — remove two-folder explanation
- `docs/learned/planning/impl-context.md` — remove copy step references
- `docs/learned/cli/plan-implement.md` — update workflow
- `docs/learned/planning/lifecycle.md`, `workflow.md`, `worktree-cleanup.md`
- `docs/learned/glossary.md`

### Project-level docs

- `AGENTS.md` — `.impl/` references in planning workflow section
- `docs/learned/tripwires-index.md` — planning tripwires

### `.gitignore`

Keep `.impl/` entry with transition comment:
```
# Legacy - kept for transition
.impl/
```

## Key Design Decision: CI Cleanup

The `plan-implement.yml` currently copies `.erk/impl-context/` to `.impl/`, then does `git rm -rf .erk/impl-context/` (removes from git AND disk).

New approach: `git rm -r --cached .erk/impl-context/` removes from git index only, keeping files on disk. The existing `.gitignore` entry `.erk/impl-context/` prevents re-tracking. The implementation agent then reads directly from the on-disk files.

## Verification

1. Run `make fast-ci` after Phase 1 to verify all tests pass
2. After Phase 2, test CI workflow changes with a test plan dispatch
3. Grep for remaining `.impl` references: `rg '\.impl[/"'"'"']' --type py --type md --type yaml`
4. Verify `resolve_impl_dir()` no longer has legacy fallback
5. Verify `.erk/impl-context/` is the only path constructed for plan context
