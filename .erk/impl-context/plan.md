# Add Progress Logging to One-Shot Dispatch

## Context

The TUI "Implement (One-Shot)" operation appears hung at "Running..." because `dispatch_one_shot()` performs several slow operations (GitHub API calls, LLM inference) between entering the function and its first progress message. The user sees output from `_handle_one_shot()` ("Dispatching node 1.1: ...", "Phase: ...", "Prompt: ...") and then silence for 10-30+ seconds before "Creating branch..." appears.

The goal is to add `user_output()` progress messages at key points so the TUI streaming panel shows what's happening.

## Current Output Timeline (with gaps)

```
[plan_cmd.py _handle_one_shot]
  "Dispatching node 1.1: ..."
  "Phase: ..."
  "Prompt: ..."

  --- ENTERS dispatch_one_shot() ---

  *** GAP: gh auth check, skeleton issue creation, LLM slug generation (5-15s) ***

  "Creating branch..."
  "Pushing to remote..."
  "Creating draft PR..."
  "Created draft PR #NNN"
  "Triggering one-shot workflow..."

  *** GAP: trigger_workflow polling (~5-25s) ***

  "✓ Dispatch metadata written"
  "✓ Queued event comment posted"
  "Done!"

  --- RETURNS to _handle_one_shot ---

  *** GAP: _update_objective_node API calls (~2-4s, silent) ***
```

## Changes

### File 1: `src/erk/cli/commands/one_shot_dispatch.py`

Add 3 `user_output()` calls before slow operations in `dispatch_one_shot()`:

1. **Before line 135** (`Ensure.gh_authenticated`): `user_output("Validating GitHub authentication...")`
2. **Before line 188** (`create_plan_issue`, inside `if not is_draft_pr`): `user_output("Creating skeleton plan issue...")`
3. **Before line 205** (`generate_slug_or_fallback`): `user_output("Generating branch name...")`

### File 2: `src/erk/cli/commands/objective/plan_cmd.py`

Add `user_output()` before objective node updates:

4. **Before line 680** (`_update_objective_node` in `_handle_one_shot`): `user_output("Updating objective roadmap...")`
5. **Before line 269** (`_batch_update_objective_nodes` in `_handle_all_unblocked`): `user_output("Updating objective roadmap...")`

### Not changing

- **Gateway layer** (`real.py` `trigger_workflow` polling): Already has `debug_log` for verbose mode. Adding `user_output` to the shared gateway would be a layer violation.
- **`write_dispatch_metadata` / comment posting**: Already have post-completion indicators ("✓ Dispatch metadata written", "✓ Queued event comment posted"). Pre-completion messages would be noisy.

## Expected Output After Changes

```
  "Dispatching node 1.1: ..."
  "Phase: ..."
  "Prompt: ..."
  "Validating GitHub authentication..."     ← NEW
  "Creating skeleton plan issue..."          ← NEW (github backend only)
  "Generating branch name..."               ← NEW
  "Creating branch..."
  "Pushing to remote..."
  "Creating draft PR..."
  "Created draft PR #NNN"
  "Triggering one-shot workflow..."
  "✓ Dispatch metadata written"
  "✓ Queued event comment posted"
  "Done!"
  "Updating objective roadmap..."            ← NEW
```

## Verification

1. Run existing tests: `uv run pytest tests/commands/one_shot/test_one_shot_dispatch.py`
2. Run `erk objective plan <issue> --one-shot --dry-run` to verify no crash (dry-run path skips dispatch)
3. Optionally test with a real objective to see streaming output in the TUI
