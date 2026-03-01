# Phase 5: Exec Script Terminology Standardization

Part of Objective #8381, Nodes 5.2–5.5

## Context

Objective #8381 standardizes "plan issue" → "plan" terminology across the codebase. Phases 1–4 and node 5.1 are complete. This plan covers the remaining Phase 5 nodes: renaming CLI flags, error codes, and docstring references in exec scripts, then regenerating the reference doc.

## Node 5.2: create_pr_from_session.py — NO CHANGES NEEDED

The JSON output already uses `plan_number` (not `issue_number`). This was fixed before Phase 5 started. Mark node as done.

## Node 5.3: track_learn_result.py — Rename `--plan-issue` flag and error codes

### Changes in `src/erk/cli/commands/exec/scripts/track_learn_result.py`

| Line | Old | New |
|------|-----|-----|
| 9 | `--plan-issue 456` (docstring usage example) | `--learn-plan 456` |
| 76 | `"--plan-issue"` (Click option name) | `"--learn-plan"` |
| 78 | `help="Learn plan number (required if...)"` | `help="Learn plan number (required if status is completed_with_plan)"` |
| 91 | `plan_issue: int \| None` (parameter name) | `learn_plan: int \| None` |
| 97 | docstring ref to `learn_plan_issue` | `learn_plan` |
| 100 | `completed_with_plan requires --plan-issue` (comment) | `completed_with_plan requires --learn-plan` |
| 101 | `plan_issue is None` | `learn_plan is None` |
| 104 | `error="missing-plan-issue"` | `error="missing-learn-plan"` |
| 105 | `"--plan-issue is required..."` | `"--learn-plan is required..."` |
| 110 | `should not have --plan-issue` (comment) | `should not have --learn-plan` |
| 111 | `plan_issue is not None` | `learn_plan is not None` |
| 114 | `error="unexpected-plan-issue"` | `error="unexpected-learn-plan"` |
| 115 | `"--plan-issue should not be provided..."` | `"--learn-plan should not be provided..."` |
| 131 | `plan_issue is not None` | `learn_plan is not None` |
| 134 | `error="unexpected-plan-issue"` | `error="unexpected-learn-plan"` |
| 135 | `"--plan-issue should not be provided..."` | `"--learn-plan should not be provided..."` |
| 164 | `"learn_plan_issue": plan_issue` | `"learn_plan_issue": learn_plan` |
| 191 | `learn_plan_issue=plan_issue` | `learn_plan_issue=learn_plan` |

**Keep unchanged:**
- Metadata dict key `"learn_plan_issue"` — this is the YAML schema field name stored in GitHub PR bodies
- Dataclass field `learn_plan_issue` in `TrackLearnResultSuccess` — matches metadata schema
- JSON output key `learn_plan_issue` — matches metadata schema

### Changes in `tests/unit/cli/commands/exec/scripts/test_track_learn_result.py`

- Line 86: `"--plan-issue"` → `"--learn-plan"` in CLI args
- Line 117: docstring `--plan-issue` → `--learn-plan`
- Line 143: assertion `"plan-issue is required"` → `"learn-plan is required"`
- Line 147: docstring `--plan-issue` → `--learn-plan`
- Line 161: `"--plan-issue"` → `"--learn-plan"` in CLI args
- Line 173: assertion `"should not be provided"` stays (unchanged text)
- Line 253: docstring `--plan-issue` → `--learn-plan`
- Line 274: `"--plan-issue"` → `"--learn-plan"` in CLI args
- Line 288: assertion `"plan-issue should not be provided"` → `"learn-plan should not be provided"`
- Line 311: `"--plan-issue"` → `"--learn-plan"` in CLI args

### Changes in `.claude/commands/erk/learn.md`

- Line 753: `--plan-issue <new-learn-plan-issue-number>` → `--learn-plan <learn-plan-number>`

## Node 5.4: impl_signal.py — Rename error codes and fix docstring

### Changes in `src/erk/cli/commands/exec/scripts/impl_signal.py`

| Line | Old | New |
|------|-----|-----|
| 191 | `"no-issue-reference"` | `"no-plan-reference"` |
| 304 | `"no-issue-reference"` | `"no-plan-reference"` |
| 383 | `"no-issue-reference"` | `"no-plan-reference"` |
| 408 | `"issue-not-found"` | `"plan-not-found"` |
| 408 | `f"Issue #{plan_ref.plan_id} not found"` | `f"Plan #{plan_ref.plan_id} not found"` |
| 440 | `updates issue metadata` | `updates plan metadata` |
| 441 | `updates issue metadata` | `updates plan metadata` |

### Changes in `tests/unit/cli/commands/exec/scripts/test_impl_signal.py`

- Lines 132, 152, 168, 184, 203, 478: `"no-issue-reference"` → `"no-plan-reference"` (6 occurrences)
- Line 532: `"issue-not-found"` → `"plan-not-found"`

## Node 5.5: Regenerate reference.md

Run `erk-dev gen-exec-reference-docs` to regenerate `.claude/skills/erk-exec/reference.md` from the updated Click command tree.

## Files Modified

1. `src/erk/cli/commands/exec/scripts/track_learn_result.py`
2. `tests/unit/cli/commands/exec/scripts/test_track_learn_result.py`
3. `src/erk/cli/commands/exec/scripts/impl_signal.py`
4. `tests/unit/cli/commands/exec/scripts/test_impl_signal.py`
5. `.claude/commands/erk/learn.md`
6. `.claude/skills/erk-exec/reference.md` (auto-generated)

## Verification

1. Run unit tests for both scripts:
   - `uv run pytest tests/unit/cli/commands/exec/scripts/test_track_learn_result.py -v`
   - `uv run pytest tests/unit/cli/commands/exec/scripts/test_impl_signal.py -v`
2. Regenerate reference doc: `erk-dev gen-exec-reference-docs`
3. Run `make fast-ci` to verify no regressions
