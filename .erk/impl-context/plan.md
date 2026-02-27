# Plan: Objective #8381 Phase 5 — Fix Exec Script Terminology

**Part of Objective #8381, Nodes 5.1–5.5**

## Context

Objective #8381 standardizes "plan-as-PR" terminology across the erk codebase. Phases 1–4 are complete (CLAUDE.md, AGENTS.md, skill docs, commands, CLI help, output messages, docstrings). Phase 5 focuses on the exec scripts layer (`src/erk/cli/commands/exec/scripts/`), which still uses stale "plan issue" terminology in docstrings, JSON output keys, CLI flags, and error codes.

## Scope

Five nodes, all mechanical renames scoped to exec scripts and their direct callers/tests:

| Node | Description |
|------|-------------|
| 5.1 | Fix docstrings and help text across ~18 exec scripts |
| 5.2 | Rename `issue_number` JSON key → `plan_number` in `create_pr_from_session.py` + callers |
| 5.3 | Rename `--plan-issue` flag → `--learn-plan` in `track_learn_result.py` |
| 5.4 | Rename error codes in `impl_signal.py` and `mark_impl_started/ended.py` |
| 5.5 | Regenerate `erk-exec/reference.md` from updated help text |

## Implementation

### Step 1: Node 5.1 — Docstrings and help text (18 exec scripts)

Replace "plan issue" → "plan" in module docstrings, Click help strings, and inline comments. These are all text-only changes with no behavioral impact.

**Files** (all under `src/erk/cli/commands/exec/scripts/`):

| File | Changes |
|------|---------|
| `create_pr_from_session.py` | "GitHub issue" → "GitHub PR", docstring |
| `track_learn_result.py` | "plan issue" → "plan" in docstring (3x) |
| `upload_session.py` | "plan issue" → "plan" in docstring (2x) |
| `get_plan_metadata.py` | "plan issue's plan-header" → "plan's plan-header" (2x) |
| `store_tripwire_candidates.py` | "plan issue" → "plan" (3x) |
| `plan_update_from_feedback.py` | "plan issue's plan-body" → "plan's plan-body" (3x) |
| `plan_save.py` | "plan issue" → "plan" in help text (3x) |
| `register_one_shot_plan.py` | "plan issue" → "plan" (1x) |
| `get_learn_sessions.py` | "plan issue" → "plan", "ISSUE" → "PLAN" (3x) |
| `trigger_async_learn.py` | "plan issue" → "plan" (1x) |
| `track_learn_evaluation.py` | "plan issue" → "plan" (4x) |
| `objective_fetch_context.py` | "plan issue" → "plan" (1x) |
| `get_pr_for_plan.py` | "plan issue" → "plan" (1x) |
| `get_plans_for_objective.py` | "plan issues" → "plans" (3x, keep "erk-plan label" unchanged) |
| `objective_update_after_land.py` | "plan issue number" → "plan number" (1x) |
| `land_execute.py` | "plan issue number" → "plan number" (1x) |
| `mark_impl_started.py` | "issue reference" → "plan reference" (docstring + message) |
| `mark_impl_ended.py` | "issue reference" → "plan reference" (docstring + message) |

### Step 2: Node 5.2 — JSON output key in `create_pr_from_session.py`

Rename the `issue_number` JSON output key to `plan_number`. This is an API contract change — update all callers atomically.

**Source** (`src/erk/cli/commands/exec/scripts/create_pr_from_session.py`):
- Line 89: `"issue_number": result.plan_number` → `"plan_number": result.plan_number`
- Line 100: `"issue_number": result.plan_number` → `"plan_number": result.plan_number`
- Line 15 (docstring): `"issue_number": N` → `"plan_number": N`
- Also: `"issue_url"` → `"plan_url"` (same lines, consistent rename)

**Caller** (`src/erk/cli/commands/pr/log_cmd.py`):
- Line 230-231: `if "issue_number" in data:` → `if "plan_number" in data:`
- `metadata["plan_number"] = data["issue_number"]` → `metadata["plan_number"] = data["plan_number"]`

**Tests**: Update assertions in `tests/unit/cli/commands/exec/scripts/test_create_pr_from_session.py` (if exists) and `tests/unit/cli/commands/pr/test_log_cmd.py`.

**NOT in scope**: `objective_post_action_comment.py` uses `data["issue_number"]` for the *objective* issue number (not a plan), so it stays unchanged. Similarly, `get_issue_body.py`, `update_issue_body.py`, etc. are generic issue utilities — not plan-specific.

### Step 3: Node 5.3 — CLI flag in `track_learn_result.py`

Rename the `--plan-issue` CLI flag and related identifiers. The persisted metadata key string `"learn_plan_issue"` in the plan-header schema is NOT renamed here (that's Phase 7 scope — requires schema migration across `schemas.py`, `plan_header.py`, and providers).

**Changes in `track_learn_result.py`:**
- Flag: `--plan-issue` → `--learn-plan`
- Help text: "Learn plan issue number" → "Learn plan number"
- Parameter: `plan_issue` → `learn_plan`
- All internal references to `plan_issue` variable → `learn_plan`
- Dataclass field: `TrackLearnResultSuccess.learn_plan_issue` → `learn_plan_number` (JSON output)
- Error codes: `"missing-plan-issue"` → `"missing-learn-plan"`, `"unexpected-plan-issue"` → `"unexpected-learn-plan"`
- Metadata dict: Keep key as `"learn_plan_issue"` (persisted schema), but variable changes: `"learn_plan_issue": learn_plan`
- Error messages: Update text referencing `--plan-issue` to `--learn-plan`

**Callers to update:**
- `.claude/commands/erk/learn.md` — update `--plan-issue` → `--learn-plan` in command examples
- Any workflow YAML that invokes `track-learn-result --plan-issue` (check `.github/workflows/`)
- Tests: `tests/unit/cli/commands/exec/scripts/test_track_learn_result.py`

### Step 4: Node 5.4 — Error codes in `impl_signal.py` and `mark_impl_*`

**`impl_signal.py`:**
- Lines 191, 304, 383: `"no-issue-reference"` → `"no-plan-reference"`
- Line 408: `"issue-not-found"` → `"plan-not-found"`
- Line 408 message: `f"Issue #{plan_ref.plan_id} not found"` → `f"Plan #{plan_ref.plan_id} not found"`

**`mark_impl_started.py`:**
- Line 95: `error_type="no-issue-reference"` → `"no-plan-reference"`
- Line 96: `message="No issue reference found..."` → `"No plan reference found..."`

**`mark_impl_ended.py`:**
- Same pattern as `mark_impl_started.py`

**Tests:**
- `tests/unit/cli/commands/exec/scripts/test_impl_signal.py` — update assertions for error codes (~6 locations)
- `tests/unit/cli/commands/exec/scripts/test_mark_impl_started_ended.py` — update assertions (~2 locations)

### Step 5: Node 5.5 — Regenerate reference doc

After all code changes (5.1–5.4), regenerate the auto-generated reference doc:

```bash
erk-dev gen-exec-reference-docs
```

This reads live Click command help text and updates `.claude/skills/erk-exec/reference.md`. Must run AFTER all other changes since it reflects the updated help text.

## Verification

1. Run `make fast-ci` (includes `erk-dev gen-exec-reference-docs --check` to verify reference.md is up-to-date)
2. Grep for stale terminology in exec scripts: `rg "plan issue" src/erk/cli/commands/exec/scripts/`
3. Grep for renamed error codes in tests: `rg "no-issue-reference|issue-not-found" tests/`
4. Verify JSON output key rename: `rg '"issue_number"' src/erk/cli/commands/exec/scripts/create_pr_from_session.py` (should be empty)
5. Verify flag rename: `rg "plan.issue" src/erk/cli/commands/exec/scripts/track_learn_result.py` (should be empty)
