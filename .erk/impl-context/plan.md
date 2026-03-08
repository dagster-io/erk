# Plan: @json_output Decorator + Structured Errors + One-Shot JSON

**Objective:** #9009 (Agent-Friendly CLI)
**Nodes:** 1.1 (json-output-decorator), 1.2 (structured-cli-errors), 1.3 (one-shot-json)

## Context

Erk CLI commands output human-readable styled text to stderr via `user_output()`. Agents (MCP tools, exec scripts, hooks) need structured JSON on stdout to parse results reliably. This plan creates the `@json_output` decorator infrastructure and wires it into `erk one-shot` as the steelthread.

## Step 1: Create `@json_output` decorator — `src/erk/cli/json_output.py` (NEW)

A decorator applied **above** `@click.command()` that operates on the `click.Command` object (same pattern as `@alias` in `src/erk/cli/alias.py`):

```python
def json_output(cmd: click.Command) -> click.Command:
    """Add --json flag and JSON error handling to a Click command."""
```

**What it does:**
- Appends `click.Option(["--json"], "json_mode", is_flag=True)` to `cmd.params`
- Wraps `cmd.callback` to catch `UserFacingCliError` when `json_mode=True`
- On caught error: `click.echo(json.dumps({"success": false, "error_type": ..., "message": ...}))` then `raise SystemExit(1)`
- Passes `SystemExit` and other exceptions through unchanged
- When `json_mode=False`: delegates to original callback unchanged

**No `CliJsonResult` protocol** — commands handle success JSON inline (matching existing patterns in `objective view`, `objective check`). The decorator only handles the error path uniformly.

**Helper function** for commands to emit success JSON:
```python
def emit_json(data: dict[str, Any]) -> None:
    """Emit a JSON success result to stdout. Adds success=True automatically."""
    data["success"] = True
    click.echo(json.dumps(data))
```

### Tests — `tests/unit/cli/test_json_output.py` (NEW)

Create a minimal Click command decorated with `@json_output`, test via `CliRunner`:
- `test_adds_json_flag` — `--json` appears in command params
- `test_no_flag_passes_through` — normal behavior without `--json`
- `test_catches_user_facing_error` — error serialized as JSON
- `test_preserves_error_type` — custom `error_type` in JSON output
- `test_system_exit_passes_through` — `SystemExit` not caught

## Step 2: Add `error_type` to `UserFacingCliError` — `src/erk/cli/ensure.py`

```python
class UserFacingCliError(click.ClickException):
    def __init__(self, message: str, *, error_type: str = "cli_error") -> None:
        super().__init__(message)
        self.message = message
        self.error_type = error_type
```

**Default parameter exception:** `UserFacingCliError` extends `click.ClickException` (third-party) and has ~49 existing call sites. Default avoids a 49-file migration for no benefit. New call sites that need classification use the keyword: `raise UserFacingCliError("msg", error_type="auth_required")`.

No changes to `show()` — it's only called in non-JSON mode.

## Step 3: Wire `erk one-shot --json` — Nodes 1.3

### 3a. Add `OneShotDryRunResult` — `one_shot_remote_dispatch.py`

Currently `dispatch_one_shot_remote` returns `None` for dry-run. Add a result type:

```python
@dataclass(frozen=True)
class OneShotDryRunResult:
    branch_name: str
    prompt: str
    target: str
    pr_title: str
    base_branch: str
    submitted_by: str
    model: str | None
    workflow: str
```

Changes to `dispatch_one_shot_remote`:
- Return type: `OneShotDispatchResult | OneShotDryRunResult` (was `| None`)
- Dry-run path: return `OneShotDryRunResult(...)` instead of `None`
- No `quiet` param needed — `user_output()` already writes to stderr, separate from JSON on stdout

### 3b. Wire `@json_output` on `one_shot` — `one_shot.py`

```python
@json_output                    # adds --json, catches errors as JSON
@click.command("one-shot")
# ... existing options ...
@click.pass_obj
def one_shot(ctx: ErkContext, *, json_mode: bool, ...):
```

After dispatch result, add JSON branch:
```python
if json_mode:
    if isinstance(result, OneShotDryRunResult):
        emit_json({"dry_run": True, "branch_name": result.branch_name, ...})
    elif isinstance(result, OneShotDispatchResult):
        emit_json({"dry_run": False, "pr_number": result.pr_number,
                    "pr_url": f"https://github.com/{owner}/{repo_name}/pull/{result.pr_number}",
                    "run_id": result.run_id, "run_url": ..., "branch_name": result.branch_name})
    return
```

Add `error_type` to key error raises:
- `_get_remote_github`: `error_type="auth_required"`
- Empty prompt: `error_type="invalid_input"`
- Invalid `--repo` format: `error_type="invalid_repo"`

### JSON output shapes

**Success:**
```json
{"success": true, "dry_run": false, "pr_number": 123, "pr_url": "...", "run_id": "...", "run_url": "...", "branch_name": "..."}
```

**Dry-run:**
```json
{"success": true, "dry_run": true, "branch_name": "...", "prompt": "...", "target": "owner/repo", "pr_title": "...", "base_branch": "main", "model": null, "workflow": "one-shot.yml"}
```

**Error (automatic via decorator):**
```json
{"success": false, "error_type": "auth_required", "message": "GitHub authentication required."}
```

### Tests — `tests/commands/one_shot/test_one_shot_json.py` (NEW)

Using existing `FakeRemoteGitHub` pattern from `test_one_shot.py`:
- `test_json_success` — parse JSON, verify `success`, `pr_number`, `pr_url`, `run_id`, `run_url`
- `test_json_dry_run` — verify `dry_run: true` with preview fields
- `test_json_error_empty_prompt` — verify JSON error with `error_type`
- `test_json_error_auth` — verify auth error as JSON
- `test_json_no_human_on_stdout` — verify stdout is pure JSON (use `CliRunner(mix_stderr=False)`)

### Existing test updates

- `tests/commands/one_shot/test_one_shot.py` — dry-run test asserts `result is None`; update to assert `isinstance(result, OneShotDryRunResult)` if test calls dispatch directly (check actual test)
- `tests/commands/one_shot/test_one_shot_remote_dispatch.py` — same

## Files Summary

| File | Change |
|------|--------|
| `src/erk/cli/json_output.py` | **NEW** — `json_output` decorator + `emit_json` helper |
| `src/erk/cli/ensure.py` | Add `error_type` kwarg to `UserFacingCliError.__init__` |
| `src/erk/cli/commands/one_shot.py` | Add `@json_output`, JSON output branches, error types |
| `src/erk/cli/commands/one_shot_remote_dispatch.py` | Add `OneShotDryRunResult`, return type change |
| `tests/unit/cli/test_json_output.py` | **NEW** — decorator unit tests |
| `tests/commands/one_shot/test_one_shot_json.py` | **NEW** — one-shot JSON tests |

## Verification

1. `uv run pytest tests/unit/cli/test_json_output.py` — decorator tests
2. `uv run pytest tests/commands/one_shot/` — all one-shot tests (new + existing)
3. Type check and lint via devrun agent
4. `erk one-shot "test" --dry-run --json` — manual smoke test

## Key files reference

| File | Role |
|------|------|
| `src/erk/cli/alias.py` | Reference: decorator operating on `click.Command` |
| `src/erk/cli/ensure.py:33` | `UserFacingCliError` class |
| `src/erk/cli/commands/one_shot.py` | CLI entry point |
| `src/erk/cli/commands/one_shot_remote_dispatch.py:37-53` | `OneShotDispatchParams`, `OneShotDispatchResult` |
| `src/erk/cli/commands/objective/check_cmd.py:306` | Reference: existing JSON output pattern |
| `packages/erk-shared/src/erk_shared/output/output.py` | `user_output()` (stderr), `machine_output()` (stdout) |
| `tests/commands/one_shot/test_one_shot.py` | Reference: existing test pattern with `FakeRemoteGitHub` |
