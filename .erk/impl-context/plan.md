# Harden `/erk:objective-update-with-landed-pr`

## Context

The `/erk:objective-update-with-landed-pr` command orchestrates objective updates after a PR lands. It's called by `erk land` via `stream_command_with_feedback` (always with `--auto-close`), spawning a new Claude session. The current design requires the agent to execute 5+ sequential commands across 7 steps (173 lines of instructions), parsing JSON output at each step and constructing the next command. Most of this work is deterministic — only prose reconciliation genuinely requires LLM judgment.

**Problems identified:**
1. **Agent burden**: Step 2 requires the agent to extract plan references from roadmap YAML and pass them as flags — deterministic work that should be in Python
2. **Speed**: 5 sequential command executions, each requiring LLM parse → construct → execute cycles
3. **Complexity**: 173 lines of instructions with many conditionals; high risk of LLM skipping steps or improvising
4. **Redundant validation**: Step 6 re-fetches the objective to validate what we just wrote
5. **Sister command bug**: `objective-update-with-closed-plan` calls `objective-fetch-context --plan` but that flag doesn't exist
6. **Table status inference**: `_replace_table_in_text()` defaults PR presence to `in-progress` (correct by design, but undocumented)

## Plan

### 1. Create `erk exec objective-apply-landed-update`

New exec script that combines Steps 1, 2, and 4 into a single call.

**File**: `src/erk/cli/commands/exec/scripts/objective_apply_landed_update.py`

**What it does (single invocation):**
- Fetches context (objective, plan, PR, roadmap) — reuses logic from `objective_fetch_context.py`
- Updates matched roadmap nodes to `done` with PR reference, **automatically preserving existing plan references** from the parsed roadmap (eliminates agent parsing burden)
- Posts a mechanical action comment (date, PR, phase/step, roadmap_updates derived from PR title/plan body)
- Returns rich JSON with everything the agent needs for prose reconciliation

**CLI interface:**
```
erk exec objective-apply-landed-update [--pr <N>] [--objective <N>] [--branch <name>]
```

**Output JSON:**
```json
{
  "success": true,
  "objective": { "number": 6423, "title": "...", "url": "...", "objective_content": "..." },
  "plan": { "number": 6513, "title": "...", "body": "..." },
  "pr": { "number": 6517, "title": "...", "body": "...", "url": "..." },
  "roadmap": {
    "matched_steps": ["1.1", "1.2"],
    "all_complete": true,
    "summary": { "done": 5, "pending": 0 },
    "next_node": null
  },
  "node_updates": [
    { "node_id": "1.1", "previous_plan": "#6513", "previous_pr": null }
  ],
  "action_comment_id": 12345
}
```

**Implementation approach**: Import functions directly from the existing scripts rather than shelling out. This means single API fetch for the issue body, no intermediate JSON serialization, and atomic behavior (if node update fails, action comment isn't posted).

**Key functions to import:**
- `objective_fetch_context.py`: `_build_roadmap_context`, auto-discovery chain logic
- `update_objective_node.py`: `_replace_node_refs_in_body`, `_replace_table_in_text`, `_find_node_refs`
- `objective_post_action_comment.py`: `_format_action_comment`

**Files to modify:**
- New: `src/erk/cli/commands/exec/scripts/objective_apply_landed_update.py`
- New: `packages/erk-shared/src/erk_shared/objective_apply_landed_update_result.py` (TypedDict)
- Modify: `src/erk/cli/commands/exec/group.py` (register command)
- New: `tests/unit/cli/commands/exec/scripts/test_objective_apply_landed_update.py`

### 2. Restructure the command file (~70 lines)

Rewrite `.claude/commands/erk/objective-update-with-landed-pr.md` from 7 steps / 173 lines to 3 steps / ~70 lines:

**Step 1: Apply Mechanical Updates** — single `erk exec objective-apply-landed-update` call
**Step 2: Prose Reconciliation** — agent reviews `objective_content` vs PR/plan, updates comment if stale
**Step 3: Closing Triggers** — use `all_complete` from Step 1 output, handle `--auto-close`

Key simplifications:
- No YAML parsing instructions for the agent
- No plan reference extraction burden
- No `update-objective-node` command construction
- No `objective-post-action-comment` stdin JSON construction
- No separate validation step (validation done within exec script)

### 3. Add `--plan` flag to `objective-fetch-context`

Fix the bug in `objective-update-with-closed-plan` by adding `--plan` option to `objective_fetch_context.py`:

```python
@click.option("--plan", "plan_number", type=int, default=None, help="Plan number (direct lookup)")
```

When `--plan` is provided, skip branch-based plan discovery and use `plan_backend.get_plan(repo_root, str(plan_number))` directly. ~15 lines added.

**File**: `src/erk/cli/commands/exec/scripts/objective_fetch_context.py`

### 4. Document the table status inference

Add a clarifying comment to `_replace_table_in_text()` in `update_objective_node.py` lines 133-140 explaining that PR presence defaults to `in-progress` (not `done`) by design — callers who know PR is merged must pass `--status done` explicitly.

### 5. Fix `objective-update-with-closed-plan` secondary issues

- Update to use `erk exec objective-post-action-comment` instead of raw `gh issue comment`
- Update the `objective-fetch-context` invocation to use the new `--plan` flag correctly

**File**: `.claude/commands/erk/objective-update-with-closed-plan.md`

## What stays unchanged

- `run_objective_update_after_land()` in `objective_helpers.py` — calls the command by name, interface unchanged
- Existing exec scripts (`objective-fetch-context`, `update-objective-node`, `objective-post-action-comment`) — kept for other callers (plan-save, closed-plan variant)
- Fail-open invariant — maintained by `stream_command_with_feedback`
- `--auto-close` flag behavior — passes through to closing logic section

## Verification

1. Run unit tests for the new exec script: `pytest tests/unit/cli/commands/exec/scripts/test_objective_apply_landed_update.py`
2. Run existing objective tests to verify no regressions: `pytest tests/unit/cli/commands/exec/scripts/test_update_objective_node.py tests/unit/cli/commands/exec/scripts/test_objective_update_after_land.py`
3. Run full CI: `make fast-ci`
4. Manual test: land a PR linked to an objective and verify the objective updates correctly
