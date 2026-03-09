# Add `release_notes` MCP Tool to erk-mcp Server

## Context

The erk-mcp server currently exposes three tools: `plan_list`, `plan_view` (hand-written), and `one_shot` (auto-discovered). Users need the ability to view erk release notes and changelog through the MCP interface so external clients (like Claude Desktop) can answer "what's new?" questions.

The `erk release-notes` CLI command already exists as a top-level command with `--all` and `--version` flags. This plan adds a hand-written MCP tool that delegates to it, following the same pattern as `plan_list` and `plan_view`.

## Changes

### 1. Add `release_notes` function to `packages/erk-mcp/src/erk_mcp/server.py`

Add a new tool function **after** the existing `plan_view` function (before `create_mcp`):

```python
def release_notes(version: str | None = None) -> str:
    """View erk release notes and changelog.

    Shows what's new in erk, including added features, changes, and fixes.
    Call this when users ask "what's new", want to see release notes, or
    ask about the changelog.

    By default returns notes for the current installed version.
    Pass version to see notes for a specific version (e.g., "0.2.1"),
    or pass "all" to see the full changelog.
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

This follows the exact same pattern as `plan_list`:
- Uses `_run_erk()` (the standard wrapper that raises on non-zero exit)
- Builds args list conditionally based on parameters
- Returns `result.stdout`

### 2. Register the tool in `create_mcp()`

In the `create_mcp()` function, add `server.tool()(release_notes)` alongside the existing hand-written tool registrations:

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

### 3. Update tests in `packages/erk-mcp/tests/test_server.py`

#### 3a. Add `release_notes` to the import block

Update the import from `erk_mcp.server` to include `release_notes`:

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

Add a new test class **after** `TestPlanView` and **before** `TestRunErkJson`, following the same mock pattern as `TestPlanList` and `TestPlanView`:

```python
class TestReleaseNotes:
    """Tests for release_notes MCP tool."""

    @patch("erk_mcp.server._run_erk")
    def test_without_version(self, mock_run_erk: patch) -> None:
        mock_run_erk.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="[0.2.1] - 2025-01-15\n  Added:\n    • New feature", stderr=""
        )

        result = release_notes(version=None)

        assert result == "[0.2.1] - 2025-01-15\n  Added:\n    • New feature"
        mock_run_erk.assert_called_once_with(["release-notes"])

    @patch("erk_mcp.server._run_erk")
    def test_with_specific_version(self, mock_run_erk: patch) -> None:
        mock_run_erk.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="[0.2.0] notes", stderr=""
        )

        result = release_notes(version="0.2.0")

        assert result == "[0.2.0] notes"
        mock_run_erk.assert_called_once_with(["release-notes", "--version", "0.2.0"])

    @patch("erk_mcp.server._run_erk")
    def test_with_all_versions(self, mock_run_erk: patch) -> None:
        mock_run_erk.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="Full changelog", stderr=""
        )

        result = release_notes(version="all")

        assert result == "Full changelog"
        mock_run_erk.assert_called_once_with(["release-notes", "--all"])
```

#### 3c. Update `test_registers_expected_tools`

Update the expected tool set to include `release_notes`:

```python
def test_registers_expected_tools(self) -> None:
    server = create_mcp()
    tools = asyncio.run(server.list_tools())
    tool_names = {t.name for t in tools}

    assert tool_names == {"plan_list", "plan_view", "release_notes", "one_shot"}
```

## Files NOT Changing

- `src/erk/cli/commands/info/release_notes_cmd.py` — The CLI command already exists and works correctly
- `src/erk/core/release_notes.py` — Core release notes logic is unchanged
- `CHANGELOG.md` — Explicitly excluded per prompt
- `docs/learned/integrations/mcp-integration.md` — Documentation update is out of scope (can be done separately)
- `packages/erk-mcp/src/erk_mcp/__main__.py` — Entry point unchanged
- `packages/erk-mcp/src/erk_mcp/__init__.py` — No changes needed

## Verification

1. Run the erk-mcp test suite:
   ```bash
   make test-erk-mcp
   ```
   All tests should pass, including the new `TestReleaseNotes` tests and the updated `test_registers_expected_tools`.

2. Run type checking:
   ```bash
   ty check packages/erk-mcp/
   ```

3. Run formatting/linting:
   ```bash
   ruff check packages/erk-mcp/ && ruff format --check packages/erk-mcp/
   ```