# Plan: Rename JSON Output Fields in Exec Scripts

Part of Objective #9109, Node 2.1

## Context

Objective #9109 renames "plan" terminology to "pr" across all APIs. Phase 1 (gateway ABCs, core types, metadata schemas) landed in PR #9110. Node 2.1 is the first node of Phase 2, targeting JSON output fields emitted by exec scripts — the CLI-facing contract that skills, commands, and workflows consume.

## Goal

Rename four JSON output field names across ~30 exec scripts in `src/erk/cli/commands/exec/scripts/`:

| Old Field | New Field |
|-----------|-----------|
| `plan_number` | `pr_number` |
| `plan_id` | `pr_number` |
| `plan_url` | `pr_url` |
| `plan_title` | `pr_title` |

## Scope

**In scope:** JSON output dicts, dataclass fields used in JSON output, docstring examples, and input stream field names in exec scripts.

**Out of scope (but noted as dependencies):** Consumer updates in `.claude/commands/` (~21 files), `.github/workflows/` (~7 files), and `.claude/skills/` that parse these JSON fields. These consumers MUST be updated in the same PR to maintain shippability. They should be covered by nodes 4.2 or a new companion node.

## Implementation

### Step 1: Rename JSON output dict keys (mechanical bulk rename)

For each exec script file, rename string keys in `json.dumps()` calls, return dicts, and `result[...]` assignments:

**Files with `"plan_number"` → `"pr_number"` (output dicts):**
- `add_plan_label.py` (line ~59)
- `close_pr.py` (line ~76)
- `create_pr_from_session.py` (line ~123)
- `detect_plan_from_branch.py` (line ~53)
- `impl_init.py` (line ~161)
- `plan_save.py` (line ~347)
- `plan_update.py` (line ~168)
- `setup_impl.py` (lines ~77, ~307)
- `setup_impl_from_pr.py` (lines ~210, ~256, ~297)
- `objective_save_to_issue.py` (lines ~155, ~265)
- `get_plan_metadata.py` (dataclass field line ~30)
- `post_workflow_started_comment.py` (docstring line ~36)
- `track_learn_evaluation.py` (docstring line ~14)

**Files with `"plan_id"` → `"pr_number"` (output dicts):**
- `create_impl_context_from_plan.py` (line ~88, docstring ~18)
- `fetch_sessions.py` (line ~125, docstring ~11)
- `get_learn_sessions.py` (docstring ~15)
- `get_plan_info.py` (line ~63, docstring ~9)
- `get_pr_context.py` (line ~91)
- `incremental_dispatch.py` (line ~165)
- `push_and_create_pr.py` (line ~88)
- `push_session.py` (lines ~145, ~315, docstring ~16)
- `track_learn_result.py` (docstring ~15)
- `upload_impl_session.py` (line ~121, docstring ~11, ~20)

**Files with `"plan_url"` → `"pr_url"` (output dicts):**
- `create_impl_context_from_plan.py` (line ~89)
- `plan_update.py` (line ~169)
- `setup_impl_from_pr.py` (lines ~211, ~257, ~298)

**Files with `"plan_title"` → `"pr_title"` (output dicts):**
- `incremental_dispatch.py` (line ~167)
- `setup_impl_from_pr.py` (lines ~213, ~259, ~300)

### Step 2: Rename input stream field names

Scripts that read JSON from stdin also use these field names as input:

- `add_plan_labels.py` — reads `"plan_number"` from stdin JSON items (~lines 82, 89, 112, 156, 165, 174)
- `close_prs.py` — reads `"plan_number"` from stdin JSON items (~lines 82, 89, 112, 156, 165, 177, 187)

### Step 3: Rename dataclass fields used in JSON serialization

- `impl_signal.py` — `SignalSuccess.plan_number` field (line ~66)
- `get_plan_metadata.py` — `MetadataSuccess.plan_number` field (line ~30)

### Step 4: Update docstring examples

All docstring JSON examples in the files above that show the old field names.

## Approach

Use the `rename-swarm` skill to perform the bulk mechanical renames across all ~30 files. This is ideal — it's a consistent string replacement across many files.

Four passes:
1. `"plan_number"` → `"pr_number"` across all exec script files
2. `"plan_id"` → `"pr_number"` across all exec script files
3. `"plan_url"` → `"pr_url"` across all exec script files
4. `"plan_title"` → `"pr_title"` across all exec script files

Then manual review for dataclass fields (`plan_number: int` → `pr_number: int`) which are not simple string key replacements.

## Key Files

- All files under `src/erk/cli/commands/exec/scripts/` (primary targets)
- `src/erk/cli/commands/exec/scripts/impl_signal.py` (dataclass)
- `src/erk/cli/commands/exec/scripts/get_plan_metadata.py` (dataclass)

## Verification

1. Run `ruff check` and `ty` to catch any syntax/type errors
2. Run `pytest tests/unit/` to verify no test breakage
3. Grep for any remaining `"plan_number"`, `"plan_id"`, `"plan_url"`, `"plan_title"` in exec scripts to confirm completeness
4. Run `pytest tests/integration/` for broader coverage
