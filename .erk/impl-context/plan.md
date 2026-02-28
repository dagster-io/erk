# Plan: Add `_trigger_one_shot` handler and `--prompt`/`--file` options to `launch_cmd.py`

**Part of Objective #8470, Node 1.1**

## Context

Objective #8470 adds one-shot modification of existing PRs. Currently `erk one-shot` creates a new branch/PR from scratch. The goal is to enable `erk launch one-shot --prompt "fix X" --pr 123` to trigger a one-shot workflow against an **existing** PR's branch.

Node 1.1 adds the CLI entry point: the `_trigger_one_shot` handler in `launch_cmd.py` with `--prompt`/`--file` options on the `launch` command. Nodes 1.2 and 1.3 complete the workflow and planning support.

## Implementation

### Phase 1: Add CLI options and handler to `launch_cmd.py`

**File: `src/erk/cli/commands/launch_cmd.py`**

1. **Add `--prompt` option** to the `launch` Click command:
   ```python
   @click.option(
       "--prompt",
       type=str,
       default=None,
       help="Prompt text for one-shot workflow",
   )
   ```

2. **Add `--file` / `-f` option** to the `launch` Click command:
   ```python
   @click.option(
       "-f", "--file", "file_path",
       type=click.Path(exists=True, dir_okay=False),
       default=None,
       help="Read prompt from a file (one-shot only)",
   )
   ```

3. **Add `prompt` and `file_path` parameters** to the `launch()` function signature.

4. **Add `_trigger_one_shot()` handler** following the established pattern from `_trigger_pr_address`:
   - Require `--pr` (target PR)
   - Require prompt (from `--prompt` or `--file`, mutually exclusive)
   - Validate PR is OPEN
   - Get `submitted_by` via `ctx.github.check_auth_status()`
   - Build workflow inputs: `prompt`, `branch_name`, `pr_number`, `submitted_by`, `modify_existing: "true"`
   - Pass `model` if provided
   - Call `_trigger_workflow(ctx, repo, workflow_name="one-shot", ...)`

5. **Add dispatch case** in `launch()`:
   ```python
   elif workflow_name == "one-shot":
       # Resolve prompt from --prompt or --file
       ...mutual exclusivity check...
       Ensure.invariant(pr_number is not None, "--pr is required for one-shot workflow")
       _trigger_one_shot(ctx, repo, pr_number=pr_number, prompt=prompt, model=model)
   ```

6. **Add import** for `Path` (used by `--file` reading).

7. **Update docstring** to list `one-shot` in available workflows and examples.

### Phase 2: Add tests

**File: `tests/commands/launch/test_launch_cmd.py`**

Add tests following the established pattern in the file:

1. `test_workflow_launch_one_shot_triggers_workflow` - Happy path: `--pr 123 --prompt "fix X"` triggers workflow with correct inputs
2. `test_workflow_launch_one_shot_with_file` - File input: `--pr 123 --file prompt.md` reads prompt from file
3. `test_workflow_launch_one_shot_requires_pr` - Error: one-shot without `--pr` fails
4. `test_workflow_launch_one_shot_requires_prompt` - Error: one-shot without `--prompt` or `--file` fails
5. `test_workflow_launch_one_shot_prompt_and_file_exclusive` - Error: both `--prompt` and `--file` fails

## Key Design Decisions

- **Uses `_trigger_workflow`** (not `dispatch_one_shot`): Targets existing PR's branch, no new branch/PR creation needed
- **`modify_existing: "true"` in inputs**: Prepares for node 1.2 (workflow support). The workflow ignores unknown inputs, so this is safe now.
- **`submitted_by` from auth status**: Matches how `dispatch_one_shot` gets the submitter identity
- **Prompt resolution in dispatch block**: The `--prompt`/`--file` resolution happens in the `launch()` dispatch block (not the handler) since the options are on the command, keeping the handler signature clean with just `prompt: str`

## Files to Modify

| File | Change |
|------|--------|
| `src/erk/cli/commands/launch_cmd.py` | Add `--prompt`, `--file` options, `_trigger_one_shot` handler, dispatch case |
| `tests/commands/launch/test_launch_cmd.py` | Add 5 tests for one-shot handler |

## Verification

1. Run tests: `uv run pytest tests/commands/launch/test_launch_cmd.py -v`
2. Run type checker: `uv run ty check src/erk/cli/commands/launch_cmd.py`
3. Run linter: `uv run ruff check src/erk/cli/commands/launch_cmd.py`
