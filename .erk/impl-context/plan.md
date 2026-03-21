# Eliminate all references to `erk-plan`

## Context

The `erk-plan` label/concept has been replaced by `erk-pr`. GitHub label filtering already uses `erk-pr`. The remaining `erk-plan` references are in metadata block keys, docstrings, comments, tests, and docs. This change eliminates all remaining references.

## Key Risk: Backward Compatibility

Existing GitHub PRs have `<!-- erk:metadata-block:erk-plan -->` HTML comment markers. The block registry must continue parsing these old blocks. Strategy: add a backward-compat alias `"erk-plan"` in the registry pointing to the same schema.

## Changes

### 1. Source Code (Python)

**Constant rename** (`BlockKeys.ERK_PLAN` → `BlockKeys.ERK_PR`):
- `packages/erk-shared/src/erk_shared/gateway/github/metadata/types.py:23` — rename constant + value
- `packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py:100,103,144` — docstrings + `get_key()` return
- `packages/erk-shared/src/erk_shared/gateway/github/metadata/registry.py:58-62` — update to `BlockKeys.ERK_PR`, add backward-compat `"erk-plan"` alias entry
- `src/erk/cli/commands/pr/log_cmd.py:192,200,216` — update `BlockKeys.ERK_PR`, add `"erk-plan"` backward-compat entry in extractors dict, update docstrings

**Docstring/comment updates:**
- `packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py:244,253` — docstrings
- `packages/erk-shared/src/erk_shared/gateway/github/metadata/plan_header.py:1` — module docstring
- `packages/erk-shared/src/erk_shared/gateway/github/objective_issues.py:124,168` — comments

**String literals:**
- `src/erk/cli/commands/exec/scripts/objective_plan_setup.py:69` — error message
- `packages/erk-shared/src/erk_shared/gateway/git/commit_ops/real.py:88` — temp file prefix

**Statusline (`erk_plan` underscore variant):**
- `packages/erk-statusline/src/erk_statusline/statusline.py:272,279,303,306` — rename `erk_plan` → `erk_pr` in frontmatter parsing, accept both for backward compat

### 2. Test Files (~18 files)

Replace `"erk-plan"` string literals with `"erk-pr"`, `BlockKeys.ERK_PLAN` with `BlockKeys.ERK_PR`, `erk_plan` with `erk_pr`:

- `tests/unit/gateways/github/metadata_blocks/test_plan_wrapping.py` — HTML summary tags
- `tests/unit/gateways/github/metadata_blocks/test_round_trip.py` — sample data keys
- `tests/unit/gateways/github/metadata_blocks/test_plan_issue_schema.py` — schema key assertions, HTML markers
- `tests/unit/gateways/github/metadata_blocks/test_block_type_registry.py` — registry key checks
- `tests/unit/pr_store/test_planned_pr_backend.py`
- `tests/commands/pr/test_remote_paths.py` — HTML comment markers in fixture data
- `tests/commands/pr/test_dispatch.py`
- `tests/commands/dash/test_filtering.py`
- `tests/tui/test_plan_table.py`
- `tests/core/test_impl_issue_wt_workflow.py`
- `tests/unit/objective_issues/test_label_definitions.py` — **special case**: test asserts `"erk-plan" not in labels`. Since `"erk-pr"` IS a valid label, this test assertion must change (verify label IS present or remove the negative assertion)
- `tests/integration/test_real_git_commit_ops.py`
- `packages/erk-shared/tests/unit/github/test_objective_issues.py`
- `packages/erk-shared/tests/unit/test_pr_utils.py` — HTML summary tag assertions
- `packages/erk-statusline/tests/test_statusline.py` — `erk_plan: true/false` frontmatter → `erk_pr: true/false`

### 3. Documentation (~30 .md files)

Replace `erk-plan` with `erk-pr` in all docs/learned/, .claude/commands/, .claude/skills/ files.

**Do NOT modify:** `CHANGELOG.md` (historical), `.claude/skills/erk-planning/SKILL.md` (already [REMOVED] tombstone).

### 4. Not changing

- `pyproject.toml` reference to `erk-planning` skill — it's the skill directory name, not the `erk-plan` concept
- `src/erk/capabilities/skills/bundled.py` and `src/erk/core/capabilities/codex_portable.py` — these reference the `erk-planning` skill name (already [REMOVED]), not the `erk-plan` block key

## Verification

1. Run `rg "erk-plan" --type py` — should only show backward-compat aliases and the `erk-planning` skill tombstone
2. Run `rg "erk-plan" docs/` — should return nothing
3. Run `rg "ERK_PLAN" --type py` — should return nothing
4. Run `rg "erk_plan" --type py` — should only show backward-compat in statusline
5. Run tests via devrun agent: `make fast-ci`
