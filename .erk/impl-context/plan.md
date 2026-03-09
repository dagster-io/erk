# Fix `erk one-shot` MCP tool returning empty string

## Context

The `one_shot` MCP tool in `packages/erk-mcp/src/erk_mcp/server.py` invokes `erk one-shot <prompt>` via subprocess and returns `result.stdout`. However, the CLI command writes all its output (including PR URL and workflow run URL) to **stderr** via `user_output()`, and never writes anything to **stdout**. This causes the MCP tool to return an empty string `""`.

The root cause is a two-part design gap:

1. **CLI side**: The `one_shot` Click command in `src/erk/cli/commands/one_shot.py` calls `dispatch_one_shot_remote()` which returns an `OneShotDispatchResult` dataclass (with `pr_number`, `run_id`, `branch_name`), but the Click command **discards the return value** — it never writes structured output to stdout.

2. **MCP side**: The MCP `one_shot()` function calls `_run_erk(["one-shot", prompt])` and returns `result.stdout`, which is empty because nothing was written to stdout.

The fix follows the established pattern documented in `docs/learned/cli/agent-friendly-cli.md`: add a `--json` flag to `erk one-shot` that emits structured JSON to stdout via `machine_output()`, then update the MCP tool to pass `--json`.

**Important**: The `@json_output` shared decorator mentioned in `docs/learned/cli/agent-friendly-cli.md` does not exist yet (it's a planned infrastructure piece under Objective #9009). This plan implements a minimal, pragmatic `--json` flag directly in the one-shot command, consistent with the existing ad-hoc patterns used by `wt create --json` and `pr log --json`.

## Changes

### 1. Add `--json` flag to `erk one-shot` CLI command

**File: `src/erk/cli/commands/one_shot.py`**

Add a `--json` Click option to the `one_shot` command:

```python
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Output structured JSON to stdout",
)
```

Add `as_json: bool` to the function signature.

After the `dispatch_one_shot_remote()` call, capture the return value and emit JSON when `as_json` is True:

```python
import json
from erk_shared.output.output import machine_output

result = dispatch_one_shot_remote(
    remote=remote,
    owner=owner,
    repo=repo,
    params=params,
    dry_run=dry_run,
    ref=ref,
    time_gateway=ctx.time,
    prompt_executor=ctx.prompt_executor,
)

if as_json:
    if result is None:
        # dry-run mode
        output = {"success": True, "dry_run": True}
    else:
        pr_url = f"https://github.com/{owner}/{repo}/pull/{result.pr_number}"
        run_url = f"https://github.com/{owner}/{repo}/actions/runs/{result.run_id}"
        output = {
            "success": True,
            "pr_number": result.pr_number,
            "pr_url": pr_url,
            "run_url": run_url,
            "run_id": result.run_id,
            "branch_name": result.branch_name,
        }
    machine_output(json.dumps(output, indent=2))
```

Note: Use `construct_workflow_run_url()` from `erk_shared.gateway.github.parsing` and build the PR URL inline (matching the existing pattern on line 372 of `one_shot_remote_dispatch.py`). Or just use string formatting directly to avoid an extra import — both patterns exist in the codebase.

### 2. Update MCP `one_shot` tool to pass `--json`

**File: `packages/erk-mcp/src/erk_mcp/server.py`**

Change the `one_shot()` function to pass `--json` to the CLI:

```python
def one_shot(prompt: str) -> str:
    """Submit a task for fully autonomous remote execution.

    Creates a branch, draft PR, and dispatches a GitHub Actions workflow
    where Claude autonomously explores, plans, implements, and submits.

    Returns JSON with PR URL and workflow run URL after dispatch.
    """
    result = _run_erk(["one-shot", "--json", prompt])
    return result.stdout
```

The change is minimal: insert `"--json"` into the args list and update the docstring.

### 3. Update MCP server tests

**File: `packages/erk-mcp/tests/test_server.py`**

Update `TestOneShot` tests:

- **`test_passes_prompt_to_erk`**: Update expected args to include `"--json"`:
  ```python
  mock_run_erk.assert_called_once_with(["one-shot", "--json", "Fix the bug in auth"])
  ```
  Also update the mock stdout to return valid JSON:
  ```python
  mock_run_erk.return_value = subprocess.CompletedProcess(
      args=[], returncode=0,
      stdout='{"success": true, "pr_number": 42, "pr_url": "https://github.com/test/repo/pull/42", "run_url": "https://github.com/test/repo/actions/runs/123", "run_id": "123", "branch_name": "plnd/fix-bug-03-09-1234"}',
      stderr="",
  )
  ```

- **`test_propagates_runtime_error`**: Update expected args similarly (add `"--json"`).

### 4. Add test for `--json` flag on `erk one-shot` command

**File: `tests/commands/one_shot/test_one_shot.py`**

Add a new test function `test_one_shot_json_output` that:

1. Sets up the same test context as `test_one_shot_happy_path`
2. Invokes `cli` with `["one-shot", "--json", "fix the import in config.py"]`
3. Asserts `result.exit_code == 0`
4. Parses `result.output` as JSON (Click's CliRunner captures stdout)
5. Asserts the JSON contains:
   - `"success": True`
   - `"pr_number"` (integer)
   - `"pr_url"` (string containing `"/pull/"`)
   - `"run_url"` (string containing `"/actions/runs/"`)
   - `"run_id"` (string)
   - `"branch_name"` (string starting with `"plnd/"`)

Also add a test `test_one_shot_json_dry_run` that passes `["one-shot", "--json", "--dry-run", "fix something"]` and verifies the output contains `{"success": true, "dry_run": true}`.

## Implementation Details

### JSON output schema

The JSON output from `erk one-shot --json` follows the established agent-friendly CLI contract:

**Success:**
```json
{
  "success": true,
  "pr_number": 42,
  "pr_url": "https://github.com/owner/repo/pull/42",
  "run_url": "https://github.com/owner/repo/actions/runs/12345",
  "run_id": "12345",
  "branch_name": "plnd/fix-config-bug-03-09-1234"
}
```

**Dry-run:**
```json
{
  "success": true,
  "dry_run": true
}
```

### Patterns to follow

- Use `machine_output()` (from `erk_shared.output.output`) for stdout JSON, matching the existing output routing pattern
- Use `json.dumps(output, indent=2)` for consistent formatting
- The `dispatch_one_shot_remote()` function already returns `OneShotDispatchResult | None` — use it directly
- Human output continues to flow to stderr via `user_output()` unchanged — agents ignore it
- The CLI continues to work exactly as before without `--json` — no behavior change for human users

### Key decisions

- **No `@json_output` decorator**: The shared decorator infrastructure doesn't exist yet. Use the same ad-hoc `--json` flag pattern as `wt create` and `pr log`.
- **Construct URLs in the Click command**: Build `pr_url` and `run_url` from the `OneShotDispatchResult` fields in the Click command layer. The `dispatch_one_shot_remote` function already computes and displays these URLs but doesn't include them in its return value. Adding them to the return dataclass would be over-engineering since they're trivially constructable from the existing fields.
- **No changes to `OneShotDispatchResult`**: The dataclass already has all the fields needed (`pr_number`, `run_id`, `branch_name`). URLs are derived.
- **Exit code 0 always in JSON mode**: Per the agent-friendly CLI contract, `--json` mode always exits 0. Errors would be communicated via `{"success": false, ...}`. For this initial implementation, errors will still raise exceptions (which Click handles), matching the existing pattern. Full error wrapping can be added when the `@json_output` decorator is built.

## Files NOT Changing

- `src/erk/cli/commands/one_shot_remote_dispatch.py` — The dispatch function already returns the right data. No changes needed.
- `packages/erk-shared/src/erk_shared/output/output.py` — Output routing is correct as-is.
- `.github/workflows/one-shot.yml` — Workflow unchanged.
- `docs/learned/` — No doc changes (the fix aligns with existing documentation).
- `packages/erk-mcp/src/erk_mcp/__main__.py` — Server startup unchanged.
- `src/erk/cli/json_output.py` — Does not exist yet and is not created by this plan.

## Verification

1. **Unit tests pass**: Run `make test-erk-mcp` to verify MCP tests pass with the updated `--json` arg.
2. **CLI tests pass**: Run `pytest tests/commands/one_shot/` to verify the new `--json` tests pass and existing tests aren't broken.
3. **Manual verification** (if possible): Run `erk one-shot --json --dry-run "test prompt"` to verify JSON is emitted to stdout.
4. **Full CI**: Run `make ci-fast` or equivalent to verify nothing else broke.