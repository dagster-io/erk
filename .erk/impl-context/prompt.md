Add a new `release_notes` MCP tool to the erk-mcp server. 

File to modify: packages/erk-mcp/src/erk_mcp/server.py

Add a new tool function following the exact same pattern as the existing tools (plan_list, plan_view, one_shot):

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

Register it in `create_mcp()` with `server.tool()(release_notes)`.

Also update packages/erk-mcp/tests/test_server.py:
- Add a `TestReleaseNotes` class with tests for: no version, specific version, "all" versions
- Update `test_registers_expected_tools` to include "release_notes" in the expected set
- Add `release_notes` to the imports from erk_mcp.server

Do not modify CHANGELOG.md.
