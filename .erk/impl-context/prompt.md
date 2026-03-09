Add an MCP tool to erk-mcp that exposes the `erk release-notes` command.

## Context

PR #9033 is extracting the `agentclick` subpackage from `erk.cli` to `erk_shared`. As part of that work:
- `@mcp_exposed` is being moved from `src/erk/cli/mcp_exposed.py` to `packages/erk-shared/src/erk_shared/agentclick/mcp_exposed.py`
- `@json_command` is being moved to `packages/erk-shared/src/erk_shared/agentclick/json_command.py`
- `erk-mcp`'s `server.py` already uses `discover_mcp_commands` to auto-discover commands decorated with `@mcp_exposed`

## Task

Add `@mcp_exposed` decorator to the existing `erk release-notes` Click command function so it is automatically discovered and exposed as an MCP tool.

## Steps

1. Find the `erk release-notes` command — look in `src/erk/cli/commands/` for a file related to release notes or changelog. The CLI command is `erk release-notes`.

2. Add `@mcp_exposed` to the existing Click command function for `release-notes`. The decorator should be applied with an appropriate `name` and `description`:
   - `name="release_notes"` (or similar snake_case)
   - `description`: something like "Show recent changes and release notes for erk"

3. Import `mcp_exposed` from the correct location. Given that PR #9033 may or may not be merged, check whether to import from:
   - `erk_shared.agentclick.mcp_exposed` (if #9033 is merged), OR
   - `erk.cli.mcp_exposed` (if not yet merged)
   
   Look at what other commands in the same area import to determine the correct import path.

4. The `erk release-notes` command already likely uses `@json_command` or similar. If it doesn't already have `@json_command`, you do NOT need to add it — just add `@mcp_exposed` so the command is discoverable. The MCP server's `JsonCommandTool` infrastructure will handle the rest.

5. Write a test in `tests/unit/cli/test_mcp_cli_sync.py` (or similar parity test file) that verifies `release_notes` is in the auto-discovered MCP tools list.

## Verification

1. Run `uv run pytest tests/unit/cli/test_mcp_cli_sync.py -v` to verify the parity test passes
2. Run `make fast-ci` to ensure no regressions

