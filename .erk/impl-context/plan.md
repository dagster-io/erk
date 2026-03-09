# Add MCP tool for `erk release-notes` command

## Context

The `erk release-notes` command currently provides human-readable CLI output showing changelog entries. It needs to be exposed as an MCP tool so external MCP clients (e.g., Claude Desktop) can query erk's release notes programmatically.

The MCP server uses auto-discovery: CLI commands decorated with both `@json_command` and `@mcp_exposed` are automatically registered as MCP tools. The `one_shot` command is the only existing example. This plan adds `release-notes` as the second auto-discovered MCP tool.

## Changes

### 1. Create a result dataclass for JSON output

**File:** `src/erk/cli/commands/info/release_notes_cmd.py`

Create a frozen dataclass `ReleaseNotesResult` to represent the JSON output:

```python
@dataclass(frozen=True)
class ReleaseNotesResult:
    """JSON result for release-notes command."""
    version: str
    date: str | None
    categories: dict[str, list[str]]
    items: list[str]
```

This simplifies `ReleaseEntry`'s `items: list[tuple[str, int]]` and `categories: dict[str, list[tuple[str, int]]]` into flat string lists for JSON (dropping indent levels, which are presentation-only). Each item string is the raw text.

Also create a wrapper result for the command itself:

```python
@dataclass(frozen=True)
class ReleaseNotesOutput:
    """Top-level JSON result for release-notes command."""
    current_version: str
    releases: list[dict[str, Any]]
```

This needs a `to_json_dict()` method so `emit_json_result()` can serialize it. The method should return:

```python
def to_json_dict(self) -> dict[str, Any]:
    return {
        "current_version": self.current_version,
        "releases": self.releases,
    }
```

Where each release is a dict with keys: `version`, `date`, `categories`, `items`.

### 2. Add `@json_command` and `@mcp_exposed` decorators

**File:** `src/erk/cli/commands/info/release_notes_cmd.py`

Transform the `release_notes_cmd` function to support both human and JSON output:

**Decorator stack** (order matters — `@mcp_exposed` above `@json_command` above `@click.command`):

```python
@mcp_exposed(
    name="release_notes",
    description="View erk release notes and changelog entries. Returns structured release data with version, date, categories, and items.",
)
@json_command(
    output_types=(ReleaseNotesOutput,),
)
@click.command("release-notes")
@click.option("--all", "show_all", is_flag=True, help="Show all releases, not just current version")
@click.option("--version", "-v", "target_version", help="Show notes for a specific version")
def release_notes_cmd(*, json_mode: bool, show_all: bool, target_version: str | None) -> ReleaseNotesOutput | None:
```

**Key changes to the function signature:**
- Add `json_mode: bool` parameter (injected by `@json_command`)
- Change return type to `ReleaseNotesOutput | None`
- Use keyword-only parameters (`*` separator) — the existing function uses positional params which needs to change

**Implementation logic:**
- When `json_mode` is `False`: keep the existing human-readable output (unchanged behavior)
- When `json_mode` is `True`: return a `ReleaseNotesOutput` with structured data instead of calling `click.echo()`

The function should:
1. Get releases as before
2. If `json_mode`:
   - Convert `ReleaseEntry` objects to simple dicts (flattening `(text, indent_level)` tuples to just text strings)
   - Return `ReleaseNotesOutput(current_version=..., releases=[...])`
3. If not `json_mode`: execute the existing human-readable formatting code (unchanged)

**Error handling for JSON mode:**
- "No changelog found" → raise `UserFacingCliError("No changelog found", error_type="not_found")`
- "Version not found" → raise `UserFacingCliError(f"Version {target_version} not found in changelog", error_type="not_found")`
- These will be caught by `@json_command` and serialized as JSON errors automatically

**Imports to add:**

```python
from dataclasses import dataclass
from typing import Any

from erk.cli.ensure import UserFacingCliError
from erk.cli.json_command import json_command
from erk.cli.mcp_exposed import mcp_exposed
```

### 3. Update existing tests

**File:** `tests/commands/test_release_notes.py`

The existing tests invoke `release_notes_cmd` directly via `CliRunner`. Since `@json_command` adds `--json` and `--schema` params, the existing tests should continue to work because they don't pass `--json`. However, verify that:

- The `runner.invoke(release_notes_cmd, [...])` calls still work. They should, since `json_mode` defaults to `False` when not passed.
- No existing test assertions break due to output changes.

No modifications should be needed to existing tests — they test the human-readable path which remains unchanged.

### 4. Add JSON mode tests

**File:** `tests/commands/test_release_notes.py` (add to existing file)

Add tests for the JSON output path:

```python
def test_release_notes_json_mode_current_version(tmp_path: Path) -> None:
    """Test --json flag returns structured data for current version."""
    # Setup changelog, invoke with ["--json"], parse JSON output
    # Assert: {"success": true, "current_version": "1.0.0", "releases": [...]}

def test_release_notes_json_mode_all_releases(tmp_path: Path) -> None:
    """Test --json --all returns all releases as structured data."""
    # Similar setup, invoke with ["--json", "--all"]
    # Assert: all versions present in releases array

def test_release_notes_json_mode_specific_version(tmp_path: Path) -> None:
    """Test --json --version returns specific version data."""
    # Invoke with ["--json", "--version", "0.9.0"]
    # Assert: single release in releases array

def test_release_notes_json_mode_version_not_found(tmp_path: Path) -> None:
    """Test --json with non-existent version returns JSON error."""
    # Invoke with ["--json", "--version", "99.99.99"]
    # Assert: {"success": false, "error_type": "not_found", ...}

def test_release_notes_json_mode_no_changelog(tmp_path: Path) -> None:
    """Test --json with no changelog returns JSON error."""
    # Assert: {"success": false, "error_type": "not_found", ...}
```

### 5. Verify MCP parity test passes

**File:** `tests/unit/cli/test_mcp_cli_sync.py`

No changes needed to this file. The existing parity tests are generic — they walk the Click tree and verify:
- Every `@mcp_exposed` command is registered as an MCP tool
- Schema matches Click-derived schema
- No orphaned tools
- Every `@mcp_exposed` has `@json_command`

Since `release_notes_cmd` will have both decorators, it will be automatically discovered and validated by these tests.

**Potential concern:** The `release_notes_cmd` object is registered in both `cli` (top-level) and `info_group` (sub-group). `discover_mcp_commands` walks the tree recursively, so it could find the same command object twice. Both would produce a tool with the same `name="release_notes"`. In `_build_json_command_tools()`, this would create two `JsonCommandTool` instances with the same name. When added to the server, the second would overwrite the first (same behavior). The parity tests use dicts keyed by name, so they'd also deduplicate. This should work fine, but if tests fail due to duplicate discovery, add deduplication to `_build_json_command_tools()`:

```python
seen_names: set[str] = set()
for cmd, meta in discover_mcp_commands(cli):
    if meta.name in seen_names:
        continue
    seen_names.add(meta.name)
    # ... rest of loop
```

Only add this if the tests actually fail from duplicates.

## Files NOT Changing

- `packages/erk-mcp/src/erk_mcp/server.py` — No changes needed. Auto-discovery handles everything.
- `src/erk/cli/mcp_exposed.py` — No changes needed. Decorator is used as-is.
- `src/erk/cli/json_command.py` — No changes needed. Decorator is used as-is.
- `src/erk/cli/cli.py` — No changes needed. The command is already registered at top level.
- `src/erk/core/release_notes.py` — No changes needed. Core logic stays the same.
- `tests/unit/cli/test_mcp_cli_sync.py` — No changes needed. Existing parity tests cover new tool automatically.
- `CHANGELOG.md` — Never modify directly.

## Implementation Details

### Decorator stack order

The decorator stack MUST be in this order (outermost to innermost):
1. `@mcp_exposed(...)` — attaches MCP metadata
2. `@json_command(...)` — adds `--json`/`--schema` flags, wraps callback
3. `@click.command(...)` — creates the Click Command object
4. `@click.option(...)` — adds options to the command

This is because decorators execute bottom-to-top: `@click.command` creates the Command, then `@json_command` wraps it, then `@mcp_exposed` attaches metadata. See `one_shot` command for the reference pattern.

### output_types enforcement

The recent commit `79c392b06` enforces that `output_types` matches the return annotation. The function returns `ReleaseNotesOutput | None` (None for human-readable path that calls click.echo). The `output_types` should be `(ReleaseNotesOutput,)`.

However, note: when `json_mode=False`, the function calls `click.echo()` and returns `None`. When `json_mode=True`, it returns `ReleaseNotesOutput`. The `@json_command` wrapper only calls `emit_json_result()` when the return value is not `None`, so this pattern works correctly.

The test `test_output_types_matches_return_annotation` in `tests/unit/cli/test_json_command.py` checks that the output_types tuple matches the return annotation's types. For a return type of `ReleaseNotesOutput | None`, it should extract `{ReleaseNotesOutput, NoneType}` or `{ReleaseNotesOutput}`. Check how `_unwrap_return_types` handles `| None` — it likely strips `None` from the union. If `output_types=(ReleaseNotesOutput,)` passes the test, use that. If not, adjust accordingly.

### Flattening ReleaseEntry for JSON

`ReleaseEntry.items` is `list[tuple[str, int]]` and `categories` is `dict[str, list[tuple[str, int]]]`. For JSON output, flatten these:
- `items` → `list[str]` (just the text, drop indent level)
- `categories` → `dict[str, list[str]]` (just the text per category)

### Import path for mcp_exposed

The prompt mentions PR #9033 may move `mcp_exposed` to `erk_shared.agentclick.mcp_exposed`. Check the current import in `one_shot.py`:

```python
from erk.cli.mcp_exposed import mcp_exposed
```

Use the same import path. If #9033 is merged by implementation time and the import has moved, follow whatever `one_shot.py` uses.

## Verification

1. Run `uv run pytest tests/unit/cli/test_mcp_cli_sync.py -v` — parity tests pass, `release_notes` appears as discovered MCP tool
2. Run `uv run pytest tests/commands/test_release_notes.py -v` — existing human-readable tests still pass, new JSON tests pass
3. Run `uv run pytest tests/unit/cli/test_json_command.py::test_output_types_matches_return_annotation -v` — output_types enforcement passes
4. Run `make fast-ci` — full CI passes with no regressions