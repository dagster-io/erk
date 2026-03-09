# Add `release_notes` MCP Tool to erk-mcp Server

## Context

The erk-mcp server currently exposes three tools (`plan_list`, `plan_view`, `one_shot`). MCP clients need access to erk release notes and changelog information — for example, to answer "what's new in erk?" queries. The `erk release-notes` CLI command already exists as a top-level Click command, but it's not exposed via MCP.

This plan adds a hand-written `release_notes` MCP tool following the same pattern as `plan_list` and `plan_view` (delegate to `_run_erk` with CLI args).

## Changes

### 1. Add `release_notes` function in `packages/erk-mcp/src/erk_mcp/server.py`

Add a new function after `plan_view` (around line 101), before `create_mcp`:

```python
def release_notes(version: str | None = None) -> str:
    """View erk release notes and changelog — useful for "what's new" queries.

    Returns release notes text from the erk changelog.
    When version is None, shows the current version's release notes.
    When version is a specific version string like "0.2.1", shows that version's notes.
    When version is "all", shows the full changelog.
    """
    args = ["release-notes"]
    if version is not None:
        if version == "all":
            args.append("--all")
        else:
            args.extend(["--version", version])
    result = _run_erk(args)
    return result.stdout
```

Key details:
- Uses `_run_erk` (the standard wrapper that raises `RuntimeError` on non-zero exit), matching `plan_list` and `plan_view`
- The `version` parameter is `str | None = None`, matching the prompt's specification
- CLI delegation: `erk release-notes` (no version), `erk release-notes --all` (version="all"), `erk release-notes --version X.Y.Z` (specific version)
- The docstring mentions "what's new" to help MCP clients understand this is for release/changelog queries

### 2. Register the tool in `create_mcp()` in `packages/erk-mcp/src/erk_mcp/server.py`

In the `create_mcp()` function (around line 109), add `release_notes` registration alongside the other hand-written tools:

```python
def create_mcp() -> FastMCP:
    """Create and configure the FastMCP server instance."""
    from fastmcp import FastMCP

    server = FastMCP(DEFAULT_MCP_NAME)
    # Hand-written tools (no input schema class yet)
    server.tool()(plan_list)
    server.tool()(plan_view)
    server.tool()(release_notes)  # <-- ADD THIS LINE
    # Auto-discovered @mcp_exposed @json_command tools
    for tool in _build_json_command_tools():
        server.add_tool(tool)
    return server
```

### 3. Add tests in `packages/erk-mcp/tests/test_server.py`

#### 3a. Add `release_notes` to the import block (line 17)

Update the import to include `release_notes`:

```python
from erk_mcp.server import (
    JsonCommandTool,
    _build_json_command_tools,
    _run_erk,
    _run_erk_json,
    create_mcp,
    plan_list,
    plan_view,
    release_notes,  # <-- ADD
)
```

#### 3b. Add `TestReleaseNotes` test class

Add a new test class after `TestPlanView` (after line 136) and before `TestRunErkJson`. Follow the same mock pattern as `TestPlanList` and `TestPlanView`:

```python
class TestReleaseNotes:
    """Tests for release_notes MCP tool."""

    @patch("erk_mcp.server._run_erk")
    def test_without_version(self, mock_run_erk: patch) -> None:
        mock_run_erk.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="[0.3.0] - 2025-01-15\n  Added\n    - New feature", stderr=""
        )

        result = release_notes(version=None)

        assert result == "[0.3.0] - 2025-01-15\n  Added\n    - New feature"
        mock_run_erk.assert_called_once_with(["release-notes"])

    @patch("erk_mcp.server._run_erk")
    def test_with_specific_version(self, mock_run_erk: patch) -> None:
        mock_run_erk.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="[0.2.1] notes", stderr=""
        )

        result = release_notes(version="0.2.1")

        assert result == "[0.2.1] notes"
        mock_run_erk.assert_called_once_with(["release-notes", "--version", "0.2.1"])

    @patch("erk_mcp.server._run_erk")
    def test_with_all(self, mock_run_erk: patch) -> None:
        mock_run_erk.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="Full changelog content", stderr=""
        )

        result = release_notes(version="all")

        assert result == "Full changelog content"
        mock_run_erk.assert_called_once_with(["release-notes", "--all"])
```

#### 3c. Update `test_registers_expected_tools` (line 285)

Change the expected tool set to include `release_notes`:

```python
assert tool_names == {"plan_list", "plan_view", "one_shot", "release_notes"}
```

## Files NOT Changing

- `src/erk/cli/commands/info/release_notes_cmd.py` — No changes to the CLI command itself
- `src/erk/core/release_notes.py` — No changes to the core release notes logic
- `CHANGELOG.md` — Explicitly excluded per prompt
- `docs/learned/integrations/mcp-integration.md` — Documentation update is out of scope for this plan
- `src/erk/cli/mcp_exposed.py` — Not using auto-discovery; this is a hand-written tool

## Implementation Details

**Pattern**: This follows the exact hand-written tool pattern of `plan_list` and `plan_view`:
1. A module-level function with typed parameters and a descriptive docstring
2. Builds CLI args list conditionally based on parameters
3. Calls `_run_erk(args)` and returns `result.stdout`
4. Registered via `server.tool()(function_name)` in `create_mcp()`

**Why hand-written, not `@mcp_exposed`**: The `release-notes` CLI command is a standard Click command, not a `@json_command`. The `@mcp_exposed` auto-discovery only works with `@json_command` commands. Converting `release-notes` to `@json_command` is out of scope.

**Naming**: `release_notes` (snake_case) matches the existing convention (`plan_list`, `plan_view`, `one_shot`).

**The `version="all"` branch**: The `--all` flag on the CLI is a boolean flag, not a value argument. When the MCP tool receives `version="all"`, it translates to `--all` (not `--version all`). This matches the prompt specification.

## Verification

1. Run the erk-mcp tests: `make test-erk-mcp` (or `uv run --package erk-mcp pytest packages/erk-mcp/tests/`)
2. Verify all existing tests still pass (no regressions)
3. Verify the three new `TestReleaseNotes` tests pass
4. Verify `test_registers_expected_tools` passes with the updated expected set
5. Run type checking across the erk-mcp package