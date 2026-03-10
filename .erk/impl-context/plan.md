# Plan: Replace @json_command With Separate Human and Machine CLI Adapters

## Context

The current `@json_command` decorator mixes human CLI parsing, machine JSON transport, and MCP discovery in one abstraction. JSON input is merged into Click kwargs, JSON values can override CLI values, and MCP schemas are derived from Click params rather than the actual machine contract. This refactor splits into three clean layers: core operations (request/result dataclasses), human CLI adapters, and machine CLI adapters under `erk json ...`.

Source spec: `agentclick-machine-cli-plan.md` (on current branch).

## Step 1: Create the machine command infrastructure

Replace `@json_command` with a new `@machine_command` decorator in `packages/erk-shared/src/erk_shared/agentclick/`.

**New/modified files:**
- `packages/erk-shared/src/erk_shared/agentclick/machine_command.py` (NEW)
  - `MachineCommandMeta(frozen=True)` — stores `request_type`, `result_types`, `name`, `description`
  - `@machine_command(request_type=..., result_types=..., name=..., description=...)` decorator
  - Wraps a Click command that: reads stdin JSON, deserializes to request dataclass, calls core op, serializes result
  - Adds `--schema` flag (short-circuits to emit schema doc)
  - No `--json` or `--stdin-json` flags — machine commands are always JSON in/out
  - Error handling: catches `AgentCliError`, emits `{"success": false, "error_type": ..., "message": ...}`

- `packages/erk-shared/src/erk_shared/agentclick/machine_schema.py` (NEW or rename `json_schema.py`)
  - `request_schema(request_type)` — generates input schema from frozen dataclass fields (NOT Click params)
  - `result_schema(result_types)` — reuse existing `output_type_schema()` logic
  - `build_schema_document(meta: MachineCommandMeta)` — combines input/output/error schemas
  - Keep `dataclass_to_json_schema()` utility (already works well)

- Keep `packages/erk-shared/src/erk_shared/agentclick/errors.py` — `AgentCliError` unchanged
- Keep `packages/erk-shared/src/erk_shared/agentclick/json_command.py` helpers: `emit_json()`, `emit_json_result()`, `read_stdin_json()` — move to a shared `io.py` or keep in place

**Key design:** Schema generation derives from request/result dataclass fields, NOT from Click parameters. This is the whole point of the refactor.

## Step 2: Update MCP discovery to target machine commands

**Modified files:**
- `packages/erk-shared/src/erk_shared/agentclick/mcp_exposed.py`
  - `discover_mcp_commands()` should find commands with `MachineCommandMeta` (not `JsonCommandMeta`)
  - MCP metadata (`name`, `description`) moves INTO `MachineCommandMeta` — eliminate separate `@mcp_exposed` decorator
  - Discovery walks the `erk json` subtree only

- `packages/erk-mcp/src/erk_mcp/server.py`
  - `_run_erk_json()` changes command path: `["erk", "json", *command_path]` instead of `["erk", *command_path, "--json"]`
  - Stdin JSON is the request object directly (no `--stdin-json` flag needed)
  - `JsonCommandTool` updated: schema comes from `MachineCommandMeta.request_type` not `command_input_schema(cmd)`
  - `_build_json_command_tools()` discovers from `erk json` subtree

## Step 3: Create `erk json` command group

**New files:**
- `src/erk/cli/commands/json/__init__.py` — `json_group = click.group("json")`
- `src/erk/cli/commands/json/one_shot.py` — machine adapter for one-shot
- `src/erk/cli/commands/json/pr/__init__.py` — `pr_group`
- `src/erk/cli/commands/json/pr/list_cmd.py` — machine adapter for pr list
- `src/erk/cli/commands/json/pr/view_cmd.py` — machine adapter for pr view

**Modified files:**
- `src/erk/cli/cli.py` — register `json_group` on `cli`

Each machine adapter:
1. Is a bare `@click.command()` with no Click options/arguments (except `--schema`)
2. Decorated with `@machine_command(request_type=..., result_types=..., name=..., description=...)`
3. Receives parsed request dataclass
4. Calls core operation function
5. Returns result dataclass (decorator handles JSON serialization)

## Step 4: Extract core operations

**New files:**
- `src/erk/cli/commands/one_shot_operation.py`
  - `OneShotRequest(frozen=True)` — `prompt`, `model`, `dry_run`, `plan_only`, `slug`, `dispatch_ref`, `ref_current`, `target_repo`
  - `run_one_shot(request, *, ctx) -> OneShotDispatchResult | OneShotDryRunResult`
  - Reuses `dispatch_one_shot_remote()` from `one_shot_remote_dispatch.py`
  - No Click imports, no `json_stdout`

- `src/erk/cli/commands/pr/list_operation.py`
  - `PrListRequest(frozen=True)` — `label`, `state`, `run_state`, `stage`, `limit`, `all_users`, `sort`, `repo` (optional string, not `GitHubRepoId`)
  - `run_pr_list(request, *, ctx) -> PrListResult`
  - Extracted from `_pr_list_impl()`, always returns `PrListResult`, no `json_stdout` branching
  - `PrListResult` stays as-is (already frozen dataclass with `to_json_dict()`)

- `src/erk/cli/commands/pr/view_operation.py`
  - `PrViewRequest(frozen=True)` — `identifier`, `full`, `repo` (optional string)
  - `run_pr_view(request, *, ctx) -> PrViewResult`
  - Extracted from inline logic in `pr_view()` command
  - `PrViewResult` stays as-is

**Key:** Request dataclasses use simple types (strings, bools, ints) — no `GitHubRepoId` or `click.Path`. Repo resolution happens in the adapters.

## Step 5: Refactor human commands to use core operations

**Modified files:**
- `src/erk/cli/commands/one_shot.py`
  - Remove `@json_command`, `@mcp_exposed` decorators
  - Remove `json_stdout` parameter
  - Keep all Click options/arguments for human ergonomics
  - Build `OneShotRequest` from Click params (resolve `--file` to prompt text here)
  - Call `run_one_shot(request, ctx=ctx)`
  - Render result with human-friendly output
  - Remove `--json`, `--stdin-json`, `--schema` flags

- `src/erk/cli/commands/pr/list_cmd.py`
  - Remove `@json_command`, `@mcp_exposed`
  - Remove `json_stdout` parameter
  - Build `PrListRequest`, call `run_pr_list()`, render table output
  - `_pr_list_impl()` can be removed or simplified (logic moves to `run_pr_list`)

- `src/erk/cli/commands/pr/view_cmd.py`
  - Remove `@json_command`, `@mcp_exposed`
  - Remove `json_stdout` parameter
  - Build `PrViewRequest`, call `run_pr_view()`, render display output

## Step 6: Delete old infrastructure

**Delete or gut:**
- `packages/erk-shared/src/erk_shared/agentclick/json_command.py` — remove `@json_command` decorator, `JsonCommandMeta`. Keep `emit_json()`, `emit_json_result()`, `read_stdin_json()` as utilities (move if needed)
- `packages/erk-shared/src/erk_shared/agentclick/json_schema.py` — remove `command_input_schema()` (Click-param-derived). Keep `dataclass_to_json_schema()`, `output_type_schema()`
- Remove `exclude_json_input`, `required_json_input` concepts entirely

## Step 7: Rewrite tests

**Delete and replace:**
- `packages/erk-shared/tests/unit/agentclick/test_json_command.py` → `test_machine_command.py`
  - Test machine command decorator: stdin JSON parsing, result serialization, error envelopes, `--schema`
  - Test that machine commands reject mixed input
- `packages/erk-shared/tests/unit/agentclick/test_json_schema.py` → `test_machine_schema.py`
  - Test schema generation from dataclass fields (not Click params)
- `packages/erk-mcp/tests/test_server.py`
  - Update `_run_erk_json()` tests: command path is `["erk", "json", ...]`
  - Update tool discovery to find machine commands
  - Keep None-filtering and False-boolean tests
- `tests/unit/cli/test_json_command.py` → update or delete (validates `output_types` match)
- `tests/unit/cli/test_mcp_cli_sync.py` → update to check machine command tree
- `tests/commands/one_shot/test_one_shot_json.py` → rewrite against `erk json one-shot`

**New tests:**
- Core operation tests for each command (no Click, no transport)
- Human adapter tests (Click params → request mapping, human output)
- Machine adapter tests (stdin JSON → request, structured JSON output)

## Step 8: Update documentation

**Modified files:**
- `docs/learned/cli/json-command-decorator.md` → rewrite as machine-command reference
- `docs/learned/cli/adding-json-to-commands.md` → rewrite for new three-layer pattern
- `docs/learned/integrations/mcp-integration.md` → update MCP targeting `erk json` tree
- `docs/learned/cli/agent-friendly-cli.md` → update architecture description

## Verification

1. `erk one-shot --help` shows no `--json`/`--stdin-json`/`--schema` flags
2. `erk pr list --help` shows no machine flags
3. `erk pr view --help` shows no machine flags
4. `echo '{"prompt":"test"}' | erk json one-shot` → structured JSON output
5. `echo '{}' | erk json pr list` → structured JSON output
6. `echo '{"identifier":"123"}' | erk json pr view` → structured JSON output
7. `erk json one-shot --schema` → request/result schema document
8. MCP server discovers and executes via `erk json ...` paths
9. All tests pass via devrun agent (`make fast-ci`)

## Critical Files Summary

| Layer | Files |
|-------|-------|
| Machine infra | `agentclick/machine_command.py`, `agentclick/machine_schema.py` |
| Machine adapters | `commands/json/{one_shot,pr/list_cmd,pr/view_cmd}.py` |
| Core operations | `commands/{one_shot_operation,pr/list_operation,pr/view_operation}.py` |
| Human adapters | `commands/{one_shot,pr/list_cmd,pr/view_cmd}.py` (modified) |
| MCP | `erk_mcp/server.py`, `agentclick/mcp_exposed.py` |
| Deleted | `@json_command` decorator, `command_input_schema()`, `exclude/required_json_input` |
