# Add release_notes Tool to erk-mcp Server

## Context

The erk-mcp server (in `packages/erk-mcp/`) exposes erk capabilities as MCP tools via FastMCP. Currently it has three tools: `plan_list`, `plan_view`, and `one_shot`. The `erk release-notes` CLI command already exists as a top-level Click command that displays changelog entries with colored formatting.

We need to add a new MCP tool that invokes `erk release-notes` and returns its output, so MCP clients (like Claude Desktop) can show users what's new when they ask about release notes or the changelog.

## Changes

### 1. Add `release_notes` tool function to `packages/erk-mcp/src/erk_mcp/server.py`

Add a new tool function following the exact same pattern as the existing tools (`plan_list`, `plan_view`, `one_shot`):

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

Key design decisions:
- **Tool name**: `release_notes` (snake_case, matching the existing naming convention of `plan_list`, `plan_view`, `one_shot`)
- **Optional `version` parameter**: Allows viewing a specific version's notes or all notes. Default (None) shows the current version's notes.
- **Special "all" value**: Maps to the `--all` CLI flag to show the full changelog
- **Delegates to `erk release-notes`**: The CLI command is registered at the top level (line 203 of `src/erk/cli/cli.py`), so the erk CLI args are `["release-notes"]` (not `["info", "release-notes"]`)
- **Description**: Written to help AI assistants trigger the tool when users ask about "what's new", "release notes", or "changelog"

### 2. Register the tool in `create_mcp()` in `packages/erk-mcp/src/erk_mcp/server.py`

Add `server.tool()(release_notes)` alongside the existing tool registrations:

```python
def create_mcp() -> FastMCP:
    """Create and configure the FastMCP server instance."""
    from fastmcp import FastMCP

    server = FastMCP(DEFAULT_MCP_NAME)
    server.tool()(plan_list)
    server.tool()(plan_view)
    server.tool()(one_shot)
    server.tool()(release_notes)
    return server
```

### 3. Add tests in `packages/erk-mcp/tests/test_server.py`

Add a new test class `TestReleaseNotes` following the exact pattern of the existing test classes:

```python
class TestReleaseNotes:
    """Tests for release_notes MCP tool."""

    @patch("erk_mcp.server._run_erk")
    def test_without_version(self, mock_run_erk: patch) -> None:
        mock_run_erk.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="Release notes for erk 0.3.0\n...", stderr=""
        )

        result = release_notes(version=None)

        assert result == "Release notes for erk 0.3.0\n..."
        mock_run_erk.assert_called_once_with(["release-notes"])

    @patch("erk_mcp.server._run_erk")
    def test_with_specific_version(self, mock_run_erk: patch) -> None:
        mock_run_erk.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="[0.2.1] - 2025-12-11\n...", stderr=""
        )

        result = release_notes(version="0.2.1")

        assert result == "[0.2.1] - 2025-12-11\n..."
        mock_run_erk.assert_called_once_with(["release-notes", "--version", "0.2.1"])

    @patch("erk_mcp.server._run_erk")
    def test_with_all_versions(self, mock_run_erk: patch) -> None:
        mock_run_erk.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="# erk Changelog\n...", stderr=""
        )

        result = release_notes(version="all")

        assert result == "# erk Changelog\n..."
        mock_run_erk.assert_called_once_with(["release-notes", "--all"])
```

Update the `test_registers_expected_tools` test in `TestCreateMcp` to include the new tool:

```python
def test_registers_expected_tools(self) -> None:
    import asyncio

    server = create_mcp()
    tools = asyncio.run(server.list_tools())
    tool_names = {t.name for t in tools}

    assert tool_names == {"plan_list", "plan_view", "one_shot", "release_notes"}
```

Update the import line at the top of the test file to include `release_notes`:

```python
from erk_mcp.server import _run_erk, create_mcp, one_shot, plan_list, plan_view, release_notes
```

### 4. Update `docs/learned/integrations/mcp-integration.md`

Update the MCP Tools table to include the new tool:

| Tool             | Delegates To               | Purpose                                       |
| ---------------- | -------------------------- | --------------------------------------------- |
| `plan_list`      | `erk exec dash-data`       | List plans with status, labels, metadata      |
| `plan_view`      | `erk exec get-plan-info`   | View a specific plan's metadata and body      |
| `one_shot`       | `erk one-shot <prompt>`    | Submit a task for autonomous remote execution |
| `release_notes`  | `erk release-notes`        | View release notes and changelog              |

Update the count from "Three tools" to "Four tools" in the paragraph above the table.

Add a new subsection after the `one_shot` documentation:

```markdown
### `release_notes(version: str | None = None) -> str`

Returns release notes from the erk changelog. By default shows the current version's notes. Pass a version string (e.g., `"0.2.1"`) for a specific version, or `"all"` for the full changelog.
```

## Files NOT Changing

- `packages/erk-mcp/src/erk_mcp/__init__.py` - No exports needed
- `packages/erk-mcp/src/erk_mcp/__main__.py` - No changes to entry point
- `packages/erk-mcp/pyproject.toml` - No new dependencies
- `packages/erk-mcp/tests/test_main.py` - No changes to main module tests
- `src/erk/core/release_notes.py` - Existing release notes core logic unchanged
- `src/erk/cli/commands/info/release_notes_cmd.py` - Existing CLI command unchanged
- `.mcp.json` - No configuration changes needed
- `CHANGELOG.md` - Per project conventions, never modify directly

## Verification

1. Run the erk-mcp test suite: `make test-erk-mcp` (or the pytest equivalent targeting `packages/erk-mcp/tests/`)
2. Verify all 4 existing test classes pass plus the new `TestReleaseNotes` class
3. Verify the `test_registers_expected_tools` test now expects 4 tools including `release_notes`
4. Run `ruff check` and `ruff format --check` on `packages/erk-mcp/` to confirm code style